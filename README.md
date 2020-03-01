# SVGPolygoniser
A module that reads your SVG files (paths and vector graphic) and is able to categorize data given 2D coordinates.

This project is but a draft, now. But it gives some features :
- Read SVG file, extracts forms and tranforms them into matplotlib's paths. IMPORTANT NOTE : I chose not to use any parser, because Python's XML Parsers are well known to have security flaws. I made a "handmade" reader which IS NOT a parser, to avoid that issue and make this module safe.
- Transformation of coordinates (from a box to another)
- Provides a method to categorize datas from a list or series.

It now uses Shapely and is about four times faster. Thus two versions are available (SVGPolygoniser and SVGShapeliser). 

This project was originally made as a tool to enhance the visualisation of an ongoing project at the IA School (as part of the Data Science Master cursus).

Incoming features :
- Calculates and returns the center of each polygon.
- Tells the total area of a polygon.
- Another py module which will use shapely : https://pypi.org/project/Shapely/ for increased performance and easier improvability.

Feel free to contact me at : g.wael@outlook.fr
LinkedIn : https://www.linkedin.com/in/wael-gribaa/
My personal website : https://waelgribaa.wixsite.com/website

Thank you for all your support !
