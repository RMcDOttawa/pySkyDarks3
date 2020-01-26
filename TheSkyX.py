# Class to send and receive commands (Javascript commands and text responses) to the
# server running TheSkyX
import socket
import sys

from tracelog import *

from PyQt5.QtCore import QMutex

from Validators import Validators


class TheSkyX:

    MAX_RECEIVE_SIZE = 1024

    _server_mutex = QMutex()

    def __init__(self, server_address: str, port_number: int):
        # print(f"TheSkyX/init({server_address},{port_number})")
        self._server_address = server_address
        self._port_number = int(port_number)

    # Get the autosave-path string from the camera.
    # Return a success flag and the path string, and an error message if needed
    @tracelog
    def get_camera_autosave_path(self) -> (bool, str):
        """Get the autosave file path the camera will use to save image files"""
        # print("TheSkyX/get_camera_autosave_path")
        command_with_return = "var path=ccdsoftCamera.AutoSavePath;" \
                + "var Out;" \
                + "Out=path+\"\\n\";"
        (success, path_result, message) = self.send_command_with_return(command_with_return)
        return success, path_result, message

    # Tell TheSkyX to connect to the camera
    @tracelog
    def connect_to_camera(self) -> (bool, str):
        """Tell TheSkyX to connect to the camera"""
        command_line = "ccdsoftCamera.Connect();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Tell TheSkyX to disconnect from the camera
    @tracelog
    def disconnect_camera(self) -> (bool, str):
        """Tell TheSkyX to disconnect from the camera"""
        command_line = "ccdsoftCamera.Disconnect();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Tell TheSkyX to take a bias frame at given binning to the camera
    @tracelog
    def take_bias_frame(self, binning: int,
                        auto_save_file: bool,
                        asynchronous: bool) -> (bool, str):
        """Take a bias frame of given binning"""
        command: str = "ccdsoftCamera.Autoguider=false;"    # Use main camera
        command += f"ccdsoftCamera.Asynchronous={self.js_bool(asynchronous)};"  # Async or wait?
        command += "ccdsoftCamera.Frame=2;"  # Type "2" is bias frame
        command += "ccdsoftCamera.ImageReduction=0;"
        command += "ccdsoftCamera.ToNewWindow=false;"
        command += "ccdsoftCamera.ccdsoftAutoSaveAs=0;"
        command += f"ccdsoftCamera.AutoSaveOn={self.js_bool(auto_save_file)};"
        command += f"ccdsoftCamera.BinX={binning};"
        command += f"ccdsoftCamera.BinY={binning};"
        command += "ccdsoftCamera.ExposureTime=0;"
        command += "var cameraResult = ccdsoftCamera.TakeImage();"
        (success, returned_value, message) = self.send_command_with_return(command)
        if success:
            return_parts = returned_value.split("|")
            assert(len(return_parts) > 0)
            if return_parts[0] == "0":
                pass  # Result indicates success
            else:
                success = False
                message = return_parts[0]
        # print(f"take-bias-frame result: {returned_value}")
        return success, message

    # Set the camera cooling on or off and, if on, set the target temperature
    @tracelog
    def set_camera_cooling(self, cooling_on: bool, target_temperature: float) -> (bool, str):
        """Set camera cooling on or off, with given target temperature"""
        # print(f"set_camera_cooling({cooling_on},{target_temperature})")
        target_temperature_command = ""
        if cooling_on:
            target_temperature_command = f"ccdsoftCamera.TemperatureSetPoint={target_temperature};"
        command_with_return = target_temperature_command \
            + f"ccdsoftCamera.RegulateTemperature={self.js_bool(cooling_on)};" \
            + f"ccdsoftCamera.ShutDownTemperatureRegulationOnDisconnect={self.js_bool(False)};"
        (success, message) = self.send_command_no_return(command_with_return)
        return success, message

    # Get temperature from camera
    # Return success, temperature, error-message

    # simulated_temp_rise: float = 0
    # simulated_temp_counter: int = 0

    # Get temperature of the CCD camera.
    # Return a tuple with command success, temperature, error message

    @tracelog
    def get_camera_temperature(self) -> (bool, float, str):
        """Determine the temperature of the camera"""
        # print(f"get_camera_temperature()")

        # For testing, return a constant temperature a few times, then gradually let it rise
        # to test if the "abort on temperature rising above a threshold" feature is OK
        # TheSkyX.simulated_temp_counter += 1
        # if TheSkyX.simulated_temp_counter > 3:
        #     TheSkyX.simulated_temp_rise += 0.5
        # print(f"get_camera_temperature  returning simulated temperature of {TheSkyX.simulated_temp_rise}")
        # return (True, TheSkyX.simulated_temp_rise, "Simulated temperature")

        command_with_return = "var temp=ccdsoftCamera.Temperature;" \
                                + "var Out;" \
                                + "Out=temp+\"\\n\";"
        temperature = 0
        (success, temperature_result, message) = self.send_command_with_return(command_with_return)
        if success:
            temperature = Validators.valid_float_in_range(temperature_result, -270, +200)
            if temperature is None:
                success = False
                temperature = 0
                message = "Invalid Temperature Returned"
        return success, temperature, message

    # Set up the camera parameters for an image (don't actually take the image)
    #  (success, message) = server.set_camera_image(frame_type, binning, exposure_seconds)
    @tracelog
    def set_camera_image(self,
                         frame_type_code: int,  # light,bias,dark,flat = 1,2,3,4
                         binning: int,
                         exposure_seconds: float) -> (bool, str):
        """Set acquisition parameters for the camera"""
        # print(f"set_camera_image({frame_type_code},{binning},{exposure_seconds})")
        command_with_no_return = "ccdsoftCamera.Autoguider = false;" \
                                + f"ccdsoftCamera.Frame = {frame_type_code};" \
                                + "ccdsoftCamera.ImageReduction = 0;" \
                                + "ccdsoftCamera.ToNewWindow=false;" \
                                + "ccdsoftCamera.AutoSaveOn=true;" \
                                + "ccdsoftCamera.Delay = 0;" \
                                + f"ccdsoftCamera.BinX = {binning};" \
                                + f"ccdsoftCamera.BinY = {binning};"
        if frame_type_code == 2:
            command_with_no_return += f"ccdsoftCamera.ExposureTime = 0;"
        else:
            command_with_no_return += f"ccdsoftCamera.ExposureTime = {exposure_seconds};"

        (success, message) = self.send_command_no_return(command_with_no_return)
        return success, message

    # Start taking image, asynchronously (i.e. command returns right away, doesn't wait for image)
    @tracelog
    def start_image_asynchronously(self) -> (bool, str):
        """Start asynchronous acquisition of one image"""
        # print("start_image_asynchronously")
        command_with_no_return = "ccdsoftCamera.Asynchronous=true;" \
                                + "var cameraResult = ccdsoftCamera.TakeImage();" \
                                + "var Out;" \
                                + "Out=cameraResult+\"\\n\";"

        (success, result, message) = self.send_command_with_return(command_with_no_return)
        # print(f"   Returned result: {result}")
        if success and (result != "0"):
            success = False
            message = f"Error {result} from camera"
        return success, message

    #        (complete_check_successful, is_complete, message) = server.get_exposure_is_complete()
    # Ask the camera if the asynchronous exposure we started is complete
    # Return command-success,  is-complete,  error-message
    @tracelog
    def get_exposure_is_complete(self) -> (bool, bool, str):
        """Determine whether camera is still busy with asynchronous image acquisition or is done"""
        # print("get_exposure_is_complete")

        command_with_no_return = "var complete = ccdsoftCamera.IsExposureComplete;" \
                             + "var Out;" \
                             + "Out=complete+\"\\n\";"

        (command_success, result, message) = self.send_command_with_return(command_with_no_return)
        # print(f"   Returned result: {result}")
        if command_success:
            if result == "0":
                is_complete = False
            elif result == "1":
                is_complete = True
            else:
                # Something has gone wrong - e.g. the user aborted the image directly in TheSkyX
                # the result string will contain an explanation, usually terminated by "|".
                # Treat this is an exception.
                command_success = False
                message = result.split("|")[0]
                is_complete = True
        else:
            is_complete = False

        # print(f"      Success={command_success},complete={is_complete},message={message}")
        return command_success, is_complete, message

    # Send Abort to camera to stop the image in progress
    @tracelog
    def abort_image(self) -> (bool, str):
        """Abort image acquisition in progress"""
        # print("abort_image")
        command_line = "ccdsoftCamera.Abort();"
        (success, message) = self.send_command_no_return(command_line)
        return success, message

    # Send a command to the server and get a returned result value
    # Return a 3-ple:  success flag,  response,  error message if any
    @tracelog
    def send_command_with_return(self, command: str):
        """Send a command to the server that returns a result, and extract the result"""
        # print(f"send_command_with_return({command})")
        command_packet = "/* Java Script */" \
                + "/* Socket Start Packet */" \
                + command \
                + "/* Socket End Packet */"
        (success, returned_result, message) = self.send_command_packet(command_packet)
        return success, returned_result, message

    # Send a command to the server with no returned value needed
    # Return a 2-ple:  success flag,    error message if any
    @tracelog
    def send_command_no_return(self, command: str):
        """Send a command to the server that does not return a result"""
        # print(f"send_command_with_return({command})")
        command_packet = "/* Java Script */" \
                + "/* Socket Start Packet */" \
                + command \
                + "/* Socket End Packet */"
        (success, returned_result, message) = self.send_command_packet(command_packet)
        # print(f"send_command_with_return, ignoring returned result: {returned_result}")
        return success, message

    # Send command packet and read response
    # Return a 3-ple:  success flag,  response,  error message if any
    @tracelog
    def send_command_packet(self, command_packet: str):
        """Send command packet to server, read response"""
        # print(f"send_command_packet({command_packet})")
        result = ""
        success = False
        message = ""
        address_tuple = (self._server_address, self._port_number)
        TheSkyX._server_mutex.lock()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as the_socket:
            try:
                the_socket.connect(address_tuple)
                bytes_to_send = bytes(command_packet, 'utf-8')
                the_socket.sendall(bytes_to_send)
                returned_bytes = the_socket.recv(TheSkyX.MAX_RECEIVE_SIZE)
                result_lines = returned_bytes.decode('utf=8') + "\n"
                parsed_lines = result_lines.split("\n")
                if len(parsed_lines) > 0:
                    result = parsed_lines[0]
                    success = True
            except socket.gaierror as ge:
                success = False
                result = ""
                message = ge.strerror
            except ConnectionRefusedError as cr:
                success = False
                result = ""
            except Exception as ex:
                print("Unexpected error:", sys.exc_info()[0])
                print(type(ex))
                print(ex.args)
                print(ex)
                raise
                message = cr.strerror
        TheSkyX._server_mutex.unlock()
        return success, result, message

    # Convert a bool to a string in javascript-bool format (lowercase)
    @staticmethod
    def js_bool(value: bool) -> str:
        """Convert a boolean value to the string format used by JavaScript for the server"""
        return "true" if value else "false"

    # Get the cooler power level.
    # Return (success, power, message)
    @tracelog
    def get_cooler_power(self) -> (bool, float, str):
        """Ask TheSkyX for the current cooler power consumption in percent"""
        # print("get_cooler_power")
        command_with_return = "var power=ccdsoftCamera.ThermalElectricCoolerPower;" \
                + "var Out;" \
                + "Out=power+\"\\n\";"
        (success, power_result, message) = self.send_command_with_return(command_with_return)
        return success, power_result, message
