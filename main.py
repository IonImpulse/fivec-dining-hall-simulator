'''
This is a quick simulator to see how busy dining halls will be at a given time.

Uses https://api.5scheduler.io/getLocations and https://api.5scheduler.io/fullUpdate
for classroom location data and class schedule data, respectively.

Location data is formatted as such:
{
  "HarveyMudd-McGregor CompSci Center": [
    "34.10565",
    "-117.71271"
  ],
  "ClaremontMckenna-Off-Campus Crs Facility": [
    "",
    ""
  ],
  ....
}

Schedule data is formatted as such:
{
  "timestamp": 1694460912,
  "courses": [
    {
      "identifier": "AFRI-010A-AF-01",
      "id": "AFRI",
      "code": "010A",
      "dept": "",
      "section": "01",
      "title": "Intro to Africana Studies",
      "max_seats": 20,
      "seats_taken": 24,
      "seats_remaining": -4,
      "credits": 100,
      "credits_hmc": 300,
      "status": "Closed",
      "timing": [
        {
          "days": [
            "Tuesday",
            "Thursday"
          ],
          "start_time": "13:15:00",
          "end_time": "14:30:00",
          "location": {
            "school": "Pitzer",
            "building": "Lincoln",
            "room": "1135"
          }
        }
      ],
      "instructors": [
        "Jessyka Finley"
      ],
      "notes": "",
      "description": "This class will serve as a general introduction to Africana Studies. Africana studies, while still relatively young, has a vibrant history that traces the lives and scholarship of people from African descent. Its complex and latent development in academia follows from the socio-political marginalization of people within the African diaspora. Nevertheless, resilience and perseverance will be repeated themes as we study how, through different techniques and modes of understanding, people of the African diaspora have continually challenged the western hegemony of academic study. ",
      "prerequisites": "",
      "corequisites": "",
      "offered": "",
      "perm_count": 19,
      "fee": 0,
      "associations": [],
      "fulfills": [],
      "sub_term": "None"
    },
    ...
}
'''
import requests
import io
from io import BytesIO
import sys
import os
import json
import time
import datetime
import random
import asyncio
import argparse

import pygame
import math
from PIL import Image

# Define your color palette
RED = (255, 0, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)

# Other Constants
SCREEN_WIDTH = 800  # Screen width
SCREEN_HEIGHT = 800  # Screen height

# Initialize the game engine
pygame.init()

# Set the height and width of the screen
size = [SCREEN_WIDTH, SCREEN_HEIGHT]
screen = pygame.display.set_mode(size)
pygame.display.set_caption("Dining Hall Traffic Simulation")

DAY_START_TIME = 7 * 60  # 7 AM
DAY_END_TIME = 22 * 60  # 10 PM

CONVERSION_RATE = 2/5
DINNER_CONVERSION_RATE = 1/2

BOUNDING_BOX = [-117.71845, -117.70245, 34.09391, 34.10705]

DINING_HALLS = {
    "Hoch-Shanahan": {
        "location": [34.10574, -117.70980],
        "college": "HarveyMudd",
        "timing": {
            "breakfast": [7, 9],
            "lunch": [11.75, 13],
            "dinner": [17, 19]
        }
    },
    "Malott": {
        "location": [34.10284, -117.71064],
        "college": "Scripps",
        "timing": {
            "breakfast": [7.5, 10],
            "lunch": [11, 14],
            "dinner": [17, 19]
        }
    },
    "Collins": {
        "location": [34.10160, -117.70899],
        "college": "ClaremontMckenna",
        "timing": {
            "breakfast": [7.5, 10.5],
            "lunch": [11, 14],
            "dinner": [16.5, 19.5]
        }
    },
    "McConnell": {
        "location": [34.10291, -117.70562],
        "college": "Pitzer",
        "timing": {
            "breakfast": [7.5, 10],
            "lunch": [11, 13.5],
            "dinner": [17, 19.5]
        }
    },
    "Frary": {
        "location": [34.10040, -117.71073],
        "college": "Pomona",
        "timing": {
            "breakfast": [7.5, 10],
            "lunch": [11, 13.5],
            "dinner": [17, 19.5]
        }
    },
    "Frank": {
        "location": [34.09614, -117.71145],
        "college": "Pitzer",
        "timing": {
            "breakfast": [7.5, 9.5],
            "lunch": [10.5, 13.5],
            "dinner": [17, 19.5]
        }
    }
}


async def get_location_data():
    '''
    Get location data from 5C Scheduler API
    '''
    url = 'https://api.5scheduler.io/getLocations'
    response = requests.get(url)
    return response.json()


async def get_schedule_data():
    '''
    Get schedule data from 5C Scheduler API
    '''
    url = 'https://api.5scheduler.io/fullUpdate'
    response = requests.get(url)
    return response.json()

def convert_str_to_loc(loc):
    '''
    Convert a string location to a list of floats
    '''
    try :
        return [float(loc[0]), float(loc[1])]
    except ValueError:
        return [0, 0]
    
def convert_loc_to_coords(loc):
    '''
    Convert the location to coordinates on the screen
    '''
    to_return = [int((loc[1] - BOUNDING_BOX[0]) / (BOUNDING_BOX[1] - BOUNDING_BOX[0]) * SCREEN_WIDTH), int((loc[0] - BOUNDING_BOX[2]) / (BOUNDING_BOX[3] - BOUNDING_BOX[2]) * SCREEN_HEIGHT)]

    # Flip so that it is correct on the screen
    to_return[1] = SCREEN_HEIGHT - to_return[1]

    return to_return
    
def deg2num(lat_deg, lon_deg, zoom):
  lat_rad = math.radians(lat_deg)
  n = 2.0 ** zoom
  xtile = int((lon_deg + 180.0) / 360.0 * n)
  ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
  return (xtile, ytile)

def num2deg(xtile, ytile, zoom):
  """
  http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
  This returns the NW-corner of the square. 
  Use the function with xtile+1 and/or ytile+1 to get the other corners. 
  With xtile+0.5 & ytile+0.5 it will return the center of the tile.
  """
  n = 2.0 ** zoom
  lon_deg = xtile / n * 360.0 - 180.0
  lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
  lat_deg = math.degrees(lat_rad)
  return (lat_deg, lon_deg)

def getImageCluster(lat_deg, lon_deg, delta_lat,  delta_long, zoom):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}

    smurl = r"http://a.tile.openstreetmap.org/{0}/{1}/{2}.png"
    xmin, ymax = deg2num(lat_deg, lon_deg, zoom)
    xmax, ymin = deg2num(lat_deg + delta_lat, lon_deg + delta_long, zoom)

    bbox_ul = num2deg(xmin, ymin, zoom)
    bbox_ll = num2deg(xmin, ymax + 1, zoom)
    #print bbox_ul, bbox_ll

    bbox_ur = num2deg(xmax + 1, ymin, zoom)
    bbox_lr = num2deg(xmax + 1, ymax +1, zoom)
    #print bbox_ur, bbox_lr

    Cluster = Image.new('RGB',((xmax-xmin+1)*256-1,(ymax-ymin+1)*256-1) )

    for xtile in range(xmin, xmax+1):
        for ytile in range(ymin,  ymax+1):
            try:
                # Check if the tile exists
                if os.path.exists("img/" + str(zoom) + "_" + str(xtile) + "_" + str(ytile) + ".png"):
                    print("Opening: " + "img/" + str(zoom) + "_" + str(xtile) + "_" + str(ytile) + ".png")
                    # If it doesn't exist, download it
                    tile = Image.open("img/" + str(zoom) + "_" + str(xtile) + "_" + str(ytile) + ".png")
                else:
                    imgurl=smurl.format(zoom, xtile, ytile)
                    print("Downloading: " + imgurl)
                    imgstr = requests.get(imgurl, headers=headers)
                    tile = Image.open(BytesIO(imgstr.content))

                    # Save tile to img directory
                    if not os.path.exists("img"):
                        os.makedirs("img")

                    tile.save("img/" + str(zoom) + "_" + str(xtile) + "_" + str(ytile) + ".png")

                # Paste the image tile into the cluster
                Cluster.paste(tile, box=((xtile-xmin)*255 ,  (ytile-ymin)*255))
            except Exception as e:
                print("Couldn't download image: " + str(e) + " on line " + str(sys.exc_info()[-1].tb_lineno))
                tile = None

    return Cluster, [bbox_ll[1], bbox_ll[0], bbox_ur[1], bbox_ur[0]]

def plot_dining_halls(state):
    '''
    Plot the dining halls on the map
    '''
    for dining_hall in DINING_HALLS:
        # Get the location of the dining hall
        loc = DINING_HALLS[dining_hall]["location"]
        # Plot the location
        pygame.draw.rect(screen, RED, pygame.Rect(convert_loc_to_coords(loc)[0], convert_loc_to_coords(loc)[1], 5, 5))
        # Add the name of the dining hall with a background, along with number of people in line and eating
        font = pygame.font.SysFont('Arial', 12)
        text = font.render(f"{dining_hall}", True, BLUE, WHITE)
        textRect = text.get_rect()
        textRect.center = (convert_loc_to_coords(loc)[0], convert_loc_to_coords(loc)[1] - 10)
        screen.blit(text, textRect)

        text = font.render(f"In line: {len(state.people_in_dining_halls[dining_hall]['in_line'])}", True, BLUE, WHITE)
        textRect = text.get_rect()
        textRect.center = (convert_loc_to_coords(loc)[0], convert_loc_to_coords(loc)[1] + 10)
        screen.blit(text, textRect)

        text = font.render(f"Eating: {len(state.people_in_dining_halls[dining_hall]['eating'])}", True, BLUE, WHITE)
        textRect = text.get_rect()
        textRect.center = (convert_loc_to_coords(loc)[0], convert_loc_to_coords(loc)[1] + 30)
        screen.blit(text, textRect)
        

def plot_classrooms(location_data):
    '''
    Plot the classrooms on the map
    '''
    for classroom in location_data:
        # Get the location of the classroom
        loc = convert_str_to_loc(location_data[classroom])

        if loc == [0, 0] or in_bounds(loc) == False:
            continue

        # Add a square around the location
        pygame.draw.rect(screen, BLUE, pygame.Rect(convert_loc_to_coords(loc)[0], convert_loc_to_coords(loc)[1], 5, 5))

def in_bounds(loc):
    '''
    Check if a location is within the bounding box
    '''
    return loc[1] >= BOUNDING_BOX[0] and loc[1] <= BOUNDING_BOX[1] and loc[0] >= BOUNDING_BOX[2] and loc[0] <= BOUNDING_BOX[3]

def time_to_minutes(time):
    '''
    Convert a time string to minutes of HH:MM:SS
    '''
    return int(time.split(":")[0]) * 60 + int(time.split(":")[1])

def is_open(current_time, dining_hall):
    current_time = current_time / 60  # Convert to hours
    # Time is in minutes, dining hall is a dict with breakfast, lunch, and dinner times in float hours
    if current_time >= dining_hall["timing"]["breakfast"][0] and current_time <= dining_hall["timing"]["breakfast"][1]:
        return True
    elif current_time >= dining_hall["timing"]["lunch"][0] and current_time <= dining_hall["timing"]["lunch"][1]:
        return True
    elif current_time >= dining_hall["timing"]["dinner"][0] and current_time <= dining_hall["timing"]["dinner"][1]:
        return True
    else:
        return False
    
def minutes_to_time(minutes):
    # Return as formatte string HH:MM:SS
    return str(datetime.timedelta(minutes=minutes))

class SimState:
    '''
    Class to hold the state of the simulation
    '''

    def __init__(self, end_times, location_data, args):
        self.end_times = end_times
        self.location_data = location_data
        self.args = args

        self.current_minute = DAY_START_TIME - 1
        self.current_day = 0

        self.outside_people = []
        self.people_in_dining_halls = {}
        for dining_hall in DINING_HALLS:
            self.people_in_dining_halls[dining_hall] = {
                "in_line": [],
                "eating": [],
            }

        self.background_img = pygame.image.load("img/combined.png")

        self.log = []

    def get_next_day(self):
        # Args will have single char representation of days
        self.current_day += 1

        # Reset all dining halls and outside people
        self.outside_people = []
        for dining_hall in DINING_HALLS:
            self.people_in_dining_halls[dining_hall] = {
                "in_line": [],
                "eating": [],
            }


        if self.current_day >= len(self.args.days):
            self.current_day = None
            

    def save_to_file(self):
        '''
        Save the state of the simulation to CSV
        files, one for each dining hall.
        Keep appending to the file
        '''
        if not os.path.exists("output"):
            os.makedirs("output")

        with open(f"output/all.csv", "w") as f:
            in_line = ",".join([f"{dining_hall} - In Line" for dining_hall in DINING_HALLS])
            eating = ",".join([f"{dining_hall} - Eating" for dining_hall in DINING_HALLS])

            f.write("minute,outside," + in_line + "," + eating + "\n")

            for day in range(len(self.log)):
                day_log = self.log[day]

                for log in day_log:
                    if log == None:
                        continue

                    f.write(f"{minutes_to_time(log['minute'])},{log['outside']},")
                    f.write(",".join([str(log[dining_hall]['in_line']) for dining_hall in DINING_HALLS]) + ",")
                    f.write(",".join([str(log[dining_hall]['eating']) for dining_hall in DINING_HALLS]) + "\n")

        
        for day in range(len(self.log)):
            day_log = self.log[day]

            for dining_hall in DINING_HALLS:
                with open(f"output/{dining_hall}_{self.args.days[day]}.csv", "w") as f:
                    f.write("minute,outside,in_line,eating\n")

                    for log in day_log:
                        if log == None:
                            continue

                        f.write(f"{minutes_to_time(log['minute'])},{log['outside']},{log[dining_hall]['in_line']},{log[dining_hall]['eating']}\n")

            
            with open(f"output/all_lines_{self.args.days[day]}.csv", "w") as f:
                f.write(f"minute,outside,{','.join([dining_hall for dining_hall in DINING_HALLS])}\n")

                for log in day_log:
                    if log == None:
                        continue

                    f.write(f"{minutes_to_time(log['minute'])},{log['outside']},{','.join([str(log[dining_hall]['in_line']) for dining_hall in DINING_HALLS])}\n")

            with open(f"output/all_eating_{self.args.days[day]}.csv", "w") as f:
                f.write(f"minute,outside,{','.join([dining_hall for dining_hall in DINING_HALLS])}\n")

                for log in day_log:
                    if log == None:
                        continue

                    f.write(f"{minutes_to_time(log['minute'])},{log['outside']},{','.join([str(log[dining_hall]['eating']) for dining_hall in DINING_HALLS])}\n")

    def iterate(self):
        # Check if we need to change the day
        old_time = self.current_minute
        self.current_minute += self.args.time_interval / 60

        delta_minutes = self.current_minute - old_time

        if self.current_minute >= DAY_END_TIME:
            self.current_minute = DAY_START_TIME
            self.get_next_day()

            if self.current_day == None:
                return None
        

        # Sim will follow this order:
        # 1. People spawn outside classrooms if they have a class ending
        # 2. People move towards dining halls
        # 3. People enter dining halls and enter line
        # 4. People move from line to eating
        # 5. People move from eating to outside and despawn

        open_dining_halls = [dining_hall for dining_hall in DINING_HALLS if is_open(self.current_minute, DINING_HALLS[dining_hall])]

        # 1. People spawn outside classrooms
        if self.current_minute in self.end_times:
            for course in self.end_times[self.current_minute]:
                # Get the location of the classroom
                loc = convert_str_to_loc(self.location_data[course["location_string"]])

                if loc == [0, 0] or in_bounds(loc) == False:
                    continue

                conversion_rate = CONVERSION_RATE

                if self.current_minute >= 17 * 60:
                    conversion_rate = DINNER_CONVERSION_RATE

                # Spawn a person outside the classroom
                num_spawned = int(course["people"] * conversion_rate)

                for i in range(num_spawned):
                    speed = max(random.gauss(self.args.speed, 1), .2)
                    self.outside_people.append(Person(loc, speed))

                    if len(open_dining_halls) == 0:
                        continue

                    # Set the destination of the person to a random dining hall,
                    # weighted by distance
                    self.outside_people[-1].choose_dest(open_dining_halls)

        # 2. People move towards dining halls
        for person in self.outside_people:
            if person.destination == None:
                if len(open_dining_halls) == 0:
                    # Use conversion rate to determine if they will just
                    # despawn right now
                    if random.random() < CONVERSION_RATE:
                        self.outside_people.remove(person)
                    
                    continue
                else:
                    person.choose_dest(open_dining_halls)


            person.move_towards_fast(self.args.time_interval * person.speed)

        # 3. People enter dining halls and enter line
        to_remove = []
        for index, person in enumerate(self.outside_people):
            for dining_hall in DINING_HALLS:
                if person.in_dining_hall(dining_hall):
                    # Add the person to the line
                    time_in_line = len(self.people_in_dining_halls[dining_hall]["in_line"]) * self.args.line_time
                    
                    # Add some gaussian noise to the time in line
                    time_in_line = min(max(random.gauss(time_in_line, 10), 0) / 60, 60)

                    self.people_in_dining_halls[dining_hall]["in_line"].append(time_in_line)
                    to_remove.append(index)
                    break

        # Remove people who entered dining halls
        removed = 0
        for index in to_remove:
            self.outside_people.pop(index - removed)
            removed += 1

                    
        # 4. People move from line to eating, 5. People move from eating to outside and despawn
        for dining_hall in DINING_HALLS:
            to_remove = []
            for index, person in enumerate(self.people_in_dining_halls[dining_hall]["in_line"]):
                self.people_in_dining_halls[dining_hall]["in_line"][index] -= delta_minutes

                if self.people_in_dining_halls[dining_hall]["in_line"][index] <= 0:
                    to_remove.append(index)

            # Move people from line to eating
            total_removed = 0
            for index in to_remove:
                self.people_in_dining_halls[dining_hall]["in_line"].pop(index - total_removed)

                # Add the person to the eating list
                time_eating = max(random.gauss(self.args.eating_time, 2000), 0) / 60
                self.people_in_dining_halls[dining_hall]["eating"].append(time_eating)
                total_removed += 1
        

            # Now, move people from eating to outside
            to_remove = []
            for index, person in enumerate(self.people_in_dining_halls[dining_hall]["eating"]):
                self.people_in_dining_halls[dining_hall]["eating"][index] -= delta_minutes

                if self.people_in_dining_halls[dining_hall]["eating"][index] <= 0:
                    to_remove.append(index)

            # Remove people from eating
            total_removed = 0
            for index in to_remove:
                self.people_in_dining_halls[dining_hall]["eating"].pop(index - total_removed)
                total_removed += 1


        # Save the state of the simulation to log
        if self.current_day == len(self.log):
            self.log.append([])

        to_append = {
            "minute": self.current_minute,
            "outside": len(self.outside_people)
        }

        for dining_hall in DINING_HALLS:
            to_append[dining_hall] = {
                "in_line": len(self.people_in_dining_halls[dining_hall]["in_line"]),
                "eating": len(self.people_in_dining_halls[dining_hall]["eating"])
            }
        
        self.log[self.current_day].append(to_append)

        return True
    
    def draw(self):
        '''
        Draw each person on the map as a small red dot
        '''
        # Clear the screen
        screen.fill(WHITE)

        # Draw the map
        screen.blit(self.background_img, (0, 0))

        # Draw day and time in top left
        font = pygame.font.SysFont('Arial', 20)
        text = font.render(f"Day {self.args.days[self.current_day]} {str(datetime.timedelta(minutes=self.current_minute))}", True, BLUE, WHITE)
        textRect = text.get_rect()
        textRect.center = (100, 50)
        screen.blit(text, textRect)

        # Draw the classrooms and dining halls
        plot_classrooms(self.location_data)
        plot_dining_halls(self)

        # Draw the people
        for person in self.outside_people:
            pygame.draw.rect(screen, RED, pygame.Rect(convert_loc_to_coords(person.loc)[0], convert_loc_to_coords(person.loc)[1], 5, 5))

        # Update the screen
        pygame.display.flip()

        # Check if we need to quit
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None


class Person:
    '''
    Class to hold the state of a person
    '''
    def __init__(self, loc, speed):
        self.loc = loc
        self.speed = speed
        self.destination = None

    def move_towards_fast(self, delta_meters):
        R = 6371 * 10**3  # Earth’s radius in meters

        destination_lat, destination_lon = DINING_HALLS[self.destination]["location"]
        # converting to radians
        current_lat, current_lon, destination_lat, destination_lon = map(math.radians, [self.loc[0], self.loc[1], destination_lat, destination_lon])

        delta = delta_meters / R

        # calculate bearing (angle between points)
        dlon = destination_lon - current_lon
        y = math.sin(dlon) * math.cos(destination_lat)
        x = math.cos(current_lat) * math.sin(destination_lat) - math.sin(current_lat) * math.cos(destination_lat) * math.cos(dlon)
        bearing = math.atan2(y, x)

        # calculate new position
        lat = math.asin(math.sin(current_lat) * math.cos(delta) + math.cos(current_lat) * math.sin(delta) * math.cos(bearing))

        lon = current_lon + math.atan2(math.sin(bearing) * math.sin(delta) * math.cos(current_lat), 
                                        math.cos(delta) - math.sin(current_lat) * math.sin(lat))

        # need to mod by 2pi because the range of math.atan2 is -pi to +pi, while we need to give an output between 0 and 2pi
        lon = (lon + 3 * math.pi) % (2 * math.pi) - math.pi

        # convert back to degrees
        lat = math.degrees(lat)
        lon = math.degrees(lon)

        self.loc = [lat, lon]

    def in_dining_hall(self, dining_hall):
        '''
        Check if the person is in a dining hall
        '''
        # Calculate distance to dining hall
        distance = self.get_distance(DINING_HALLS[dining_hall]["location"])

        if distance <= 100:
            return True
        else:
            return False
        
    def get_distance(self, loc):
        '''
        Get the distance between two locations
        '''
        # Convert to radians
        loc1 = [math.radians(loc[0]), math.radians(loc[1])]
        loc2 = [math.radians(self.loc[0]), math.radians(self.loc[1])]

        # Calculate distance
        distance = math.acos(math.sin(loc1[0]) * math.sin(loc2[0]) + math.cos(loc1[0]) * math.cos(loc2[0]) * math.cos(loc1[1] - loc2[1]))

        # Convert to meters
        distance = distance * 6371 * 10**3

        return distance


    def choose_dest(self, choices):
        if len(choices) == 0:
            return None

        self.destination = random.choices(
            list(choices),
            weights=[self.get_distance(DINING_HALLS[dining_hall]["location"]) for dining_hall in choices],
            k=1
        )[0]

async def main():
    # Get args  
    parser = argparse.ArgumentParser(
                    prog='Claremont Dining Hall Traffic Simulator',
                    description='Simulates the movement of people in dining halls',
                    epilog='Text at the bottom of help')
    parser.add_argument('-d', '--days', type=str, help="Days to simulate, ex: MWF or TR", default="MTWRF")
    parser.add_argument('-t', '--time-interval', type=int, help="How long each time interval is in seconds", default=60)
    parser.add_argument('-e', '--eating-time', type=int, help="Mean time a person eats for in seconds", default=3600)
    parser.add_argument('-l', '--line-time', type=int, help="Time a person adds to the line in seconds", default=30)
    parser.add_argument('-s', '--speed', type=int, help="Mean walking speed in meters per second", default=0.8)

    args = parser.parse_args()

    print(args)

    # Get location data
    location_data = await get_location_data()
    # Get schedule data
    schedule_data = await get_schedule_data()

    cluster = getImageCluster(34.0941, -117.7150, 0.0128, 0.0112, 16)

    # Resize to screen size
    image_to_save = cluster[0].resize((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Save image to img/combined.png
    image_to_save.save("img/combined.png")

    # Build schedule by classroom
    schedule_by_classroom = {}

    for course in schedule_data["courses"]:
        for timing in course["timing"]:
            if timing["location"]["building"] not in schedule_by_classroom:
                schedule_by_classroom[timing["location"]["building"]] = []

            schedule_by_classroom[timing["location"]["building"]].append({
                "course": course,
                "timing": timing
            })

    # Build schedule by day now
    schedule_by_day = {
        "Monday": {},
        "Tuesday": {},
        "Wednesday": {},
        "Thursday": {},
        "Friday": {}
    }

    for classroom in schedule_by_classroom:
        for course in schedule_by_classroom[classroom]:
            for day in course["timing"]["days"]:
                if day not in schedule_by_day:
                    schedule_by_day[day] = {}

                if classroom not in schedule_by_day[day]:
                    schedule_by_day[day][classroom] = []

                schedule_by_day[day][classroom].append(course)

    # Sort each classroom by end time    
    for day in schedule_by_day:
        for classroom in schedule_by_day[day]:
            schedule_by_day[day][classroom].sort(key=lambda x: x["timing"]["end_time"])

    # Add all end times to a dict
    end_times = {}

    for day in schedule_by_day:
        for classroom in schedule_by_day[day]:
            for course in schedule_by_day[day][classroom]:

                timing = time_to_minutes(course["timing"]["end_time"])

                if timing not in end_times:
                    end_times[timing] = []

                end_times[timing].append({
                    "timing": course["timing"],
                    "location_string": f"{course['timing']['location']['school']}-{course['timing']['location']['building']}",
                    "people": course["course"]["seats_taken"]
                })
        
    # Now, we will simulate the traffic
    index = 0
    state = SimState(end_times, location_data, args)

    # Remove output
    for dining_hall in DINING_HALLS:
        if os.path.exists(f"output/{dining_hall}.csv"):
            os.remove(f"output/{dining_hall}.csv")

    while True:
        start = time.time()

        iter_result = state.iterate()
        
        if iter_result == None:
            break
        
        draw_result = state.draw()

        end = time.time()
        frame_time_ms = (end - start) * 1000


    
        #print(f"Time to simulate iteration {index}: {frame_time_ms} ms")
        index += 1

    state.save_to_file()
    print("Finished simulation")

# Now block on main
if __name__ == "__main__":
    asyncio.run(main())
