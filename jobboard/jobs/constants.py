"""Constants used by the JobBoard app.

We keep city names in a single place so both UI (datalist) and validation can
reuse the same source.

User requirement: UK cities only, ~50-80 well-known ones, alphabetical.
"""

from __future__ import annotations


# 70+ well-known UK cities/towns (England, Scotland, Wales, Northern Ireland).
# Alphabetical order for a nice UX and easy browser "type-to-jump" behavior.
UK_CITIES = sorted(
    {
        "Aberdeen",
        "Bath",
        "Belfast",
        "Birmingham",
        "Blackpool",
        "Bournemouth",
        "Bradford",
        "Brighton",
        "Bristol",
        "Cambridge",
        "Canterbury",
        "Cardiff",
        "Carlisle",
        "Chelmsford",
        "Chester",
        "Chichester",
        "Colchester",
        "Coventry",
        "Derby",
        "Derry",
        "Doncaster",
        "Dundee",
        "Durham",
        "Edinburgh",
        "Exeter",
        "Falkirk",
        "Glasgow",
        "Gloucester",
        "Guildford",
        "Halifax",
        "Hamilton",
        "Harrogate",
        "Hereford",
        "Huddersfield",
        "Hull",
        "Inverness",
        "Ipswich",
        "Lancaster",
        "Leeds",
        "Leicester",
        "Lincoln",
        "Liverpool",
        "London",
        "Luton",
        "Manchester",
        "Middlesbrough",
        "Milton Keynes",
        "Newcastle upon Tyne",
        "Newport",
        "Northampton",
        "Norwich",
        "Nottingham",
        "Oxford",
        "Paisley",
        "Perth",
        "Peterborough",
        "Plymouth",
        "Portsmouth",
        "Preston",
        "Reading",
        "Remote",
        "Salford",
        "Salisbury",
        "Sheffield",
        "Shrewsbury",
        "Slough",
        "Southampton",
        "St Albans",
        "Stirling",
        "Stoke-on-Trent",
        "Sunderland",
        "Swansea",
        "Swindon",
        "Truro",
        "Wakefield",
        "Warrington",
        "Watford",
        "Wigan",
        "Wolverhampton",
        "Worcester",
        "York",
    }
)


ENGLAND_CITIES = UK_CITIES
