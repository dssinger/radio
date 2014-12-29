#!/usr/bin/python
import sys, pygame
import time
import subprocess
import os
import glob


#define function that checks for mouse location
def on_click():
	click_pos = (pygame.mouse.get_pos() [0], pygame.mouse.get_pos() [1])
	#check to see if exit has been pressed
	if 270 <= click_pos[0] <= 320 and 10 <= click_pos[1] <=50:
		print "You pressed exit" 
		button(0)
	#now check to see if play was pressed
	if 20 <= click_pos[0] <= 70 and 80 <= click_pos[1] <=130:
                print "You pressed button play"
                button(1)	
	#now check to see if stop  was pressed
        if 80 <= click_pos[0] <= 135 and 80 <= click_pos[1] <=130:
                print "You pressed button stop"
                button(2)
	#now check to see if refreshed  was pressed
        if 270 <= click_pos[0] <= 320 and 70 <= click_pos[1] <=120:
                print "You pressed button refresh"
                button(3)
	#now check to see if previous  was pressed
        if 10 <= click_pos[0] <= 60 and 180 <= click_pos[1] <=230:
                print "You pressed button previous"
                button(4)

	 #now check to see if next  was pressed
        if 70 <= click_pos[0] <= 120 and 180 <= click_pos[1] <=230:
                print "You pressed button next"
                button(5)

	 #now check to see if volume down was pressed
        if 130 <= click_pos[0] <= 180 and 180 <= click_pos[1] <=230:
                print "You pressed volume down"
                button(6)

	 #now check to see if button 7 was pressed
        if 190 <= click_pos[0] <= 240 and 180 <= click_pos[1] <=230:
                print "You pressed volume up"
                button(7)

	 #now check to see if button 8 was pressed
        if 250 <= click_pos[0] <= 300 and 180 <= click_pos[1] <=230:
                print "You pressed mute"
                button(8)

	 #now check to see if button 9 was pressed
        if 15 <= click_pos[0] <= 125 and 165 <= click_pos[1] <=200:
                print "You pressed button 9"
                button(9)


#define action on pressing buttons
def button(number):
	print "You pressed button ",number
	if number == 0:    #specific script when exiting
		screen.fill(black)
		font=pygame.font.Font(None,24)
        	label=font.render("Radioplayer will continue in background", 1, (white))
        	screen.blit(label,(0,90))
		pygame.display.flip()
		time.sleep(5)
		sys.exit()

	if number == 1:	
		subprocess.call("mpc play ", shell=True)
		refresh_menu_screen()

	if number == 2:
		subprocess.call("mpc stop ", shell=True)
		refresh_menu_screen()

	if number == 3:
		subprocess.call("mpc stop ", shell=True)
		subprocess.call("mpc play ", shell=True)
		refresh_menu_screen() 
		
	if number == 4:
		subprocess.call("mpc prev ", shell=True)
		refresh_menu_screen()

	if number == 5:
		subprocess.call("mpc next ", shell=True)
		refresh_menu_screen()

	if number == 6:
		subprocess.call("mpc volume -10 ", shell=True)
		refresh_menu_screen()

	if number == 7:
		subprocess.call("mpc volume +10 ", shell=True)
		refresh_menu_screen()

	if number == 8:
		subprocess.call("mpc volume 0 ", shell=True)
		refresh_menu_screen()	

def refresh_menu_screen():
# Eventually, this will generate HTML, but for now, it just prints.
  
        print 'to mpc current'
	station = subprocess.check_output("mpc current", shell=True )
        print 'and back'
	lines=station.split(":")
	length = len(lines) 
	if length==1:
		line1 = lines[0]
		line1 = line1[:-1]
		line2 = "No additional info: "
	else:
		line1 = lines[0]
		line2 = lines[1]

	line2 = line2[:42]
	line2 = line2[:-1]
	#trap no station data
	if line1 =="":
		line2 = "Press PLAY or REFRESH"
		station_status = "stopped"
	else:
		station_status = "playing"
        station_name = line1
        additional_data = line2
        print station_name + '\n' + additional_data + '\n' + station_status 
	######## add volume number
	volume = subprocess.check_output("mpc volume", shell=True )
	volume = volume[8:]
	volume = volume[:-1]
        print volume
	####### check to see if the Radio is connected to the internet
	IP = subprocess.check_output("hostname -I", shell=True )
	IP=IP[:3]
	if IP =="192":
		network_status = "online"
		status_font = green

	else:
		network_status = "offline"
		status_font = red

        print network_status
        print	



def main():
        while 1:
          time.sleep(0.2)        
          break

#################### EVERTHING HAS NOW BEEN DEFINED ###########################

#set size of the screen
size = width, height = 320, 240

#define colours
blue = 26, 0, 255
cream = 254, 255, 25
black = 0, 0, 0
white = 255, 255, 255
yellow = 255, 255, 0
red = 255, 0, 0
green = 0, 255, 0
refresh_menu_screen()  #refresh the menu interface 
main() #check for key presses and start emergency exit

