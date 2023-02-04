# Python-StarcraftII
Coding in Python for a Starcraft II bot

This was part of an AI course. A group of people were given a Starcraft II bot, with the intent of improving it. Everyone got their own area of improvement.
My area was building placement.

Prior to my solution, the bot could only place 6 or so buildings, at random places, then no more.

My building placement strategy meant that defensive buildings should be built adjacent to base locations (center of each zone), and offensive units further away
from them (but not too far away).

To solve this, I had to:
-Divide the map into zones and mark choke-points. This can be seen in the HeatMap picture where the different colors represent different zones, and the 
pink dots represent chokepoints.
-Create an algorithm that, inside each zone, placed defensive and offensive buildings at desired spots.
-Take game specific things into account. Such as building size, upgrade potential, add-on potential etc.

DefensiveGreenOffensiveRed shows how defensive (green) and offenive (red) buildings are placed in each zone of the map.
The video StartZone illustrates how the north-western start zone would look like in-game.
