import re

from objects import glob

map_file = re.compile(
    r"^(?P<artist>.+) - (?P<title>.+) \((?P<mapper>.+)\) \[(?P<diff>.+)\]\.osu$",
)
osu_ver = re.compile(
    r"^b(?P<ver>\d{8})(?:\.(?P<subver>\d))?(?P<stream>beta|cuttingedge|dev|tourney)?$",
)

__bmap_domain = glob.config.domain.replace(".", r"\.")
np_regex = re.compile(  # yikes
    r"^\x01ACTION is (?:playing|editing|watching|listening to) "
    rf"\[https://osu\.(?:{__bmap_domain})/beatmapsets/(?P<sid>\d{{1,10}})#/?(?P<bid>\d{{1,10}})/? .+\]"
    r"(?: <(?P<mode>Taiko|CatchTheBeat|osu!mania)>)?"
    r"(?P<mods>(?: (?:-|\+|~|\|)\w+(?:~|\|)?)+)?\x01$",
)
