# pySkyDarks3
Orchestrator to take dark and bias calibration frames through a TheSkyX server.

This program is written in Python, at version 3.8.1 at time of writing this.  Python version 2 will not work.

The program is designed to operate unattended, over several nights. You establish a plan of all the dark and bias frames you would like (specifying the exposure times and binnings wanted). Then, the program can start and stop automatically at established times.  It connects to TheSkyX running on your observatory control computer (and with the "TCP Server" option enabled) and directs TheSkyX to take frames until either the plan is complete or a pre-set end time (such as dawn) occurs.  This can be repeated over several sessions to build up the complete set of desired frames.

Pre-built stand-alone executables for Mac and Windows are included. The program should also work on any other platform where Python can run, but you'll have to configure it appropriately.  (The Mac and Windows applications don't require that you have Python installed, as they include their own interpreter.)

In addition to standard python libraries, the pyQt and pyEphem packages are needed.  They can be installed with pip or via the IDE.  
