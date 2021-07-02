
class Anticheat:
	"""Small anticheat class with common cheats."""

	def __init__(
		self,
		client_ver: str,
		client_hash: str,
		web_headers: dict
	) -> None:
		self.version: str = client_ver.lower()
		self.md5: str = client_hash.lower()
		self.web_headers: dict = web_headers

	def perform(self):
		"""Runs multiple checks on provided data."""

		if not self.version or not self.md5 or not self.web_headers:
			# something fucked just return false in that case.
			return False, ""

		if "ainu" in self.web_headers or \
			self.version in ("0ainu", "b20190326.2", "b20190401.22f56c084ba339eefd9c7ca4335e246f80", "b20190906.1", "b20191223.3"):
			# ainu old client.
			return True, "Tried to use old ainu cheat client."

		if self.version == "f11423b10398dfbd7d460ab49615e997":
			# old check for ainu 2020 client.
			return True, "Tried to use 2020 ainu cheat client."

		if self.version in ("b20190226.2", "b20190716.5"):
			# hqosu checks.
			return True, "Tried to use hqosu client."

		if self.md5 == "0d9a67a7d3ba6cd75a4f496c9898c59d":
			# chloe in 2021 for fuck sake what a psycho.
			return True, "Tried to use chloe cheat client."

		# Lastly check for weird client.
		if self.version[:3] != "b20":
			# They use some weird shit.
			return True, "Tried to use weird/custom client."
