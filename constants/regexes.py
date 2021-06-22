import re

map_file = re.compile(r'^(?P<artist>.+) - (?P<title>.+) \((?P<mapper>.+)\) \[(?P<diff>.+)\]\.osu$')
osu_ver = re.compile(r'^b(?P<ver>\d{8})(?:\.(?P<subver>\d))?(?P<stream>beta|cuttingedge|dev|tourney)?$')