OSPi
====

A Python port of the Arduino based OpenSprinkler firmware V 1.8.3
-----------------------------------------------------------------
OpenSprinkler Pi (OSPi) Interval Program Demo<br/>
Creative Commons Attribution-ShareAlike 3.0 license<br/>
June 2013, http://rayshobby.net

***********
UPDATES
===========
***********

November 12 2013
--------------
(Dan)<br/>
Modified program to run on either OSPi or OSBo 

October 16 2013
--------------
(Dan)<br/>
Additions, bug fixes:<br/>
1. Fixed a bug that would cause an error in program preview when a master was enabled.<br/>
2. Changing to manual mode would clear rain delay setting, Setting rain delay in manual mode would switch to program mode - fixed.

October 11 2013
--------------
(Dan)<br/>
Additions, bug fixes:<br/>
1. Fixed a bug that would cause an error when a master was enabled and making changes to station settings.<br/>
2. added approve_pwd function and removed redundant code.<br/>
3. removed write_options function and added options.txt file to distribution.<br/>

October 4 2013
--------------
(jonathanmarsh)<br/>
Additions, bug fixes:<br/>
1. Improved options handling and passing logic<br/>
2. Added a "System Name" option to help users distinguish between multiple systems<br/>
3. Configurable station name length (increased default to 32)<br/>
4. Added logging options to options page<br/>

(Dan)<br/>
Additions, bug fixes:<br/>
1. Moved RasPi specific code into try-except blocks allowing program to run on multiple platforms<br/>
2. Added "write_options" function to create/update new style options.txt file in data directory.<br/>
3. Fixed a bug in new options code that prevented master station from being selected.<br/>
4. Fixed a bug that caused an exception when the number of expansion boards was reduced.<br/>

October 1 2013
--------------
Changes:<br/>
1. Changed the pin numbering option in the RPi.GPIO module from BCM to BOARD.<br/>

September 23 2013
--------------
Additions, bug fixes:<br/>
1. Added a new revisions page to the native web interface.<br/>
2. Modified the home.js file to show time zone info in the last run log near the bottom of the page.<br/>
3. Fixed a bug in concurrent mode that kept a station running after it's duration had expired.<br/>
4. Fixed a bug that would cause an exception (freeze the program) after the number of expansion boards was changed in Options.<br/>
5. Fixed a bug that would stop a running station and clear scheduled stations when the number of expansion boards was changed in Options.<br/>

September 10 2013
--------------
Additions, bug fixes:<br/>
1. Added a per-station "Ignore rain" option that allows a station to operate during rain delay or if a rain sensor detects rain.<br/>
2. Modified the program to use the HTTP port setting from the Options page.<br/>
3. Improved the way the program tracks current time. This simplified the code and should eliminate some timing bugs.<br/>
4. Edited Denny's init.d startup script to remove IP address and port settings no longer needed.<br/>

August 30 2013
--------------
Additions, bug fixes:<br/>
1. Modified the program to use only the time zone setting from the Options page and not the tz setting from the py.<br/>
2. Made the CPU temperature readout on the home page clickable to toggle between C and F.<br/>
3. Added a copy of Denny Fox's init.d auto startup script<br/>

August 25 2013
--------------
Additions, bug fixes:<br/>
1. Implemented improved installation and update methods using GitHub.<br/>
2. Modified the program to automatically create default config files on new installations. This also prevents existing settings from being overwritten.<br/>
3. Added a "Run now" button to the programs page. Allows a schedule program to be started at any time. This overrides (stops) any running program.<br/>
4. Added a readout of the Raspberry Pi's CPU temperature to the home page.<br/>
5. Fixed a bug that would allow a station to be stopped / started without a password ueing the HTML API.<br/>
6. Fixed a bug that would display an incorrect start day for a schedule program.<br/>

August 1 2013 Reved to firmware V 1.8.3
---------------------------------------
Now supports concurrent operation.<br/>
Additions, bug fixes:<br/>
1. Added Sequential/Concurrent option.<br/>
2. Added a function to detect Pi board rev and auto-configure GPIO pins for rev 1 boards.<br/>
3. Fixed a bug in manual mode that would cause any zone with a master association to stop the master when turned off, even if another station with a master association was still running.<br/>
4. Changed how ospi.py handles master zone associations. The program should now work with more than 3 expansion boards (untested in hardware but at least 5 expansion boards, 64 stations work in software).<br/>

July 21 2013
------------
Bug fixes:<br/>
1. Fixed a bug that kept an in progress program running after it was disabled.<br/>
2. Added error checking to prevent an 'lg' KeyError<br/>
3. When a new program was added, it became program 1 instead of being added at the end of the list. - fixed.<br/>
4. When Rain Delay was set, running stations did not stop. - Fixed.<br/>
5. Added a 1.5s delay in the screen refresh of manual Mode to allow active stations and last run log time to update.<br/>

July 19 2013
------------
Code re-factored:<br/>
1. Eliminated over 100 lines of redundant code. The code is now much closer to the micro-controller version. Manual Mode and Run-once now rely on the main loop algorithm. This eliminates potential conflicts and makes the code easier to maintain. The program should now be more stable and have fewer bugs although the UI is a little slower.<br/>
2. Changed bit-wise operations to make them more reliable.<br/>
3. Station names now accept Unicode characters allowing names to be entered in any language.<br/>
4. Faveicon now appears on all pages.<br/>
5. A small bug in the display of Master valve off time in the program preview has been fixed. The off time was 1 minute short.<br/>
6. A file named 'sd_reference.txt' has been added to the OSPi directory. It contains a list with descriptions of the values contained in the global settings dictionary variable (gv.sd) which holds most settings for the program. These values are kept in memory and also stored in the file OSPi/data/sd.json to persist across system restarts. This is for the benefit of anyone who wishes to tinker with the code.<br/>

It is recommended to re-install the entire OSPi directory from GitHub. You can keep your current settings by saving the contents of the OSPi/data directory to another location before installation, then replace the contents of the newly installed directory with your saved files.

july 10 2013
------------
Bug fixes and additions:<br/>
1. Fixed a bug that prevented zones 9+ from running.<br/>
2. The Run once program was not observing the station delay setting - Fixed<br/>
3. Made the sd variable an attribute of the gv module. All references to sd... are now gv.sd... This should potentially fix several bugs, Specifically the Rain delay seems to be working properly now.<br/>
4. The Graph Programs time marker was not recognizing the time zone setting from the Options page - fixed.<br/>
5. Time displayed on the last run line of the main page was not correct - fixed.<br/>
6. Added a faveicon which will help distinguish the OpenSprinkler tabs on the browser.<br/>
7. Added an import statement and file which provide a stub for adding user written custom functions to the interval program without modifying the program itself.<br/>

Jun 26 2013
-----------
1. Last run logging is now working for manual mode when an optional time value is selected, even if more that one station is started.<br/>
2. Fixed a bug that prevented the home page display from updating when running irrigation programs.<br/>
3. Includes a fix from Samer that allows the program preview time marker to update properly.<br/>

Jun 20, 2013
------------
This update includes:<br/>
1. Changed the way ospi.py handles time. It now uses the time zone setting from the OS options page. It also eliminates the auto daylight savings time adjustment that was causing problems for some users.<br/>
2. Fixes a bug mentioned on the forum that caused Samer's app to not update in program mode.<br/>
3. Fixes a bug that caused a program to re-start after the "Stop all stations" button was clicked.<br/>
4. A partial fix for the "last run" problems. Still need to get manual mode with an optional time setting working.<br/>
5. Added a docstring at the top of the ospi.py file with the date for version tracking.

Jun 19, 2013
------------
  Applied Samer Albahra's patch so that the program will work with Samer's mobile web app.
  Per forum discussion: http://rayshobby.net/phpBB3/viewtopic.php?f=2&t=154&start=40#p781<br/>
 

NOTE
====
This folder contains the interval program demo for OpenSprinkler Pi written by Dan Kimberling. It is compatible with the microcontroller-based OpenSprinkler firmware 1.8, the instructions of which can be found at:
  
  http://rayshobby.net/?page_id=730

The program makes use of web.py (http://webpy.org/) for the web interface. 

******************************************************
Full credit goes to Dan for his generous contributions
in porting the microcontroller firmware to Python.
******************************************************

================================================================

***********************
Installation and set up
***********************

For complete and up-to-date installation and set up instructions, see the Rays Hobby wiki page at:
http://rayshobby.net/mediawiki/index.php?title=Python_Interval_Program_for_OSPi
