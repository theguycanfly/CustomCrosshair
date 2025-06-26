Name the Python file crosshair_overlay_app.py and name your image that you want to use crosshair.png. Image needs to be 100x100 png with a transparent background I included a few examples
Alt + S to show/hide the crosshair
first project ever, try to be too harsh. Any tips on how to imporve the code are welcome as I'm a novice programmer

To compile app open cmd window in folder and run pyinstaller --onefile --windowed Custom_Crosshair_v2.py --add-data "crosshair.png;." --add-data "crosshair.ico;."

Updated 6/26/25 2:20 am for added functionality change hotkey button system try support
