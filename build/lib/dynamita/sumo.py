import ctypes
from time import time
from time import sleep
import os
import os.path
import zipfile
import tempfile
import shutil

class C_sumo_handle(ctypes.Structure):
  pass

class Sumo:
    def __init__(self, sumoPath, licenseFile):
        self.sumoPath = sumoPath
        self.licenseFile = licenseFile
        self.simulation_finished = False
        self.script_loaded = False
        self.model_loaded = False
        self.model_initialized = False

        self.datacomm_callback = None
        self.message_callback = None
        self.simulation_finished_callback = None

        self.messages = []

        # loading the Sumo core
        cwd = os.getcwd()
        os.chdir(self.sumoPath)
        self.core = ctypes.cdll.LoadLibrary(self.sumoPath + "\\sumocore.dll")
        os.chdir(cwd)

        # --------------------------------------------------------------------------------------------
        # structures and configuration needed by ctypes to use exported functions correctly
        # restype: result type (return type)
        # argtypes: argument types
        # --------------------------------------------------------------------------------------------

        self.core.csumo_model_load.restype = ctypes.c_int
        self.core.csumo_create.restype = ctypes.POINTER(C_sumo_handle)
        self.core.csumo_var_get_time_int.argtypes = [ctypes.POINTER(C_sumo_handle)]
        self.core.csumo_var_get_time_int.restype = ctypes.c_ulonglong
        self.core.csumo_var_get_time_double.argtypes = [ctypes.POINTER(C_sumo_handle)]
        self.core.csumo_var_get_time_double.restype = ctypes.c_double
        self.core.csumo_messages_get_all.restype = ctypes.c_char_p
        self.core.csumo_messages_get_all.argtypes = [ctypes.c_int , ctypes.c_char]
        self.core.csumo_command_send.argtypes = [ctypes.POINTER(C_sumo_handle), ctypes.c_char_p]
        self.core.csumo_license_is_valid.restype = ctypes.c_bool

        self.core.csumo_var_set_pvt_pos.argtypes = [ctypes.POINTER(C_sumo_handle), ctypes.c_int, ctypes.c_double]

        self.core.csumo_model_get_variable_info_pos.argtypes = [ctypes.POINTER(C_sumo_handle), ctypes.c_char_p]
        self.core.csumo_model_get_variable_info_pos.restype = ctypes.c_int

        self.core.csumo_var_get_pvt.argtypes = [ctypes.POINTER(C_sumo_handle), ctypes.c_char_p]
        self.core.csumo_var_get_pvt.restype = ctypes.c_double
        
        self.core.csumo_var_get_pvt_pos.argtypes = [ctypes.POINTER(C_sumo_handle), ctypes.c_int]
        self.core.csumo_var_get_pvt_pos.restype = ctypes.c_double

        self.core.csumo_var_get_pvtarray_pos.argtypes = [ctypes.POINTER(C_sumo_handle), ctypes.c_int, ctypes.c_int]
        self.core.csumo_var_get_pvtarray_pos.restype = ctypes.c_double

        def datacomm_callback(handle):
            if self.datacomm_callback is not None:
                return self.datacomm_callback(self);
            else:
                return 0

        def message_callback(handle):
            m = self.core.csumo_messages_get_all(handle, b';')

            if m is not None:
                for i in m.decode('utf8').split(';'):
                    if '530036' in i: self.script_loaded = True
                    if '530049' in i: self.model_initialized = True
                    if '530004' in i: self.simulation_finished = True
                    self.messages.append(i)
            if self.message_callback is not None:
                return self.message_callback(self);
            else:
                return 0

        def simulation_finished_callback(handle):
            self.simulation_finished = True
            if self.simulation_finished_callback is not None:
                return self.simulation_finished_callback(self);
            else:
                return 0

        CMPFUNC = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int)

        self.c_datacomm_callback = CMPFUNC(datacomm_callback)
        self.c_message_callback = CMPFUNC(message_callback)
        self.c_simulation_finished_callback = CMPFUNC(simulation_finished_callback)

        # so let's start the engine...
        self.handle = self.core.csumo_create()
        if not self.core.csumo_license_is_valid(self.handle, self.licenseFile.encode('utf8')):
            print("License not valid. Exiting...")
            exit()
        else:
            print("License OK...")

    def load_model(self, project_name):
        if self.model_loaded:
            print('A model is already loaded. Unload it before loading the next one.')
            return -1

        self.tempdir = tempfile.mkdtemp()
        project = zipfile.ZipFile(project_name, 'r')
        project.extractall(self.tempdir)
        project.close()

        model_name = os.path.join(self.tempdir, 'sumoproject.dll').encode('utf8')

        load_result = self.core.csumo_model_load(self.handle, model_name)
        if load_result != 0:
            print('Error during model load...')
            return load_result

        self.core.csumo_datacomm_callback_register(self.handle, self.c_datacomm_callback)
        self.core.csumo_message_callback_register(self.handle, self.c_message_callback)
        self.core.csumo_datacomm_simulation_finished_register(self.handle, self.c_simulation_finished_callback)

        self.core.csumo_start_core_session(self.handle, 1)

        while not self.model_initialized:
            sleep(1)

        self.model_loaded = True
        return load_result
		
    def unload_model(self):
        if not self.model_loaded:
            print('No model is loaded')
            return
        self.core.csumo_model_unload(self.handle)
        shutil.rmtree(self.tempdir)
        self.model_loaded = False

    def run_model(self):
        if not self.model_loaded:
            print('No model loaded')
            return
        self.simulation_finished = False
        self.core.csumo_command_send(self.handle, b"start;")

    def set_stopTime(self, stopTime):
        if not self.model_loaded:
            print('No model loaded')
            return
        stopTimeCommand = 'set Sumo__StopTime ' + str(stopTime) + ';'
        self.core.csumo_command_send(self.handle, stopTimeCommand.encode('utf8'))

    def set_dataComm(self, dataComm):
        if not self.model_loaded:
            print('No model loaded')
            return
        dataCommCommand = 'set Sumo__DataComm ' + str(dataComm) + ';'
        self.core.csumo_command_send(self.handle, dataCommCommand.encode('utf8'))

    def register_datacomm_callback(self, datacomm_callback):
        self.datacomm_callback = datacomm_callback;

    def register_message_callback(self, message_callback):
        self.message_callback = message_callback

    def register_simulation_finished_callback(self, simulation_finished_callback):
        self.simulation_finished_callback = simulation_finished_callback
        
