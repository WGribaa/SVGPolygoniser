import re
import matplotlib.path as mpath


class Polygoniser:
    """
    Polygoniser will tell if a 2D geometrical path contains a list of points.
    It is adapted to DataFrame formats.
    """
    polygons_ = {}
    view_box_ = None

    def __init__(self, path_files, box=None, invert_y=True):
        """
        Constructor.
        :param path_files: For the moment, path_files can only be a string representing a SVG file with multiple paths.
        :param box: Box in which to scale the point coordinates. Form : (x_start, y_start, x_end, y_end)
        :param invert_y: tells if the y coordinates are inverted. Specifically, pictures have a reverse y coordinate
        ((0,0) is the upper left corner of the picture).
        """
        self.data_box_ = box
        self.invert_y = invert_y
        # if isinstance(path_files, list):
        #     for filepath in path_files:
        #         sep_index = max(filepath.rfind(os.sep), 0)
        #         comma_index = filepath[sep_index:].find(".")
        #         if comma_index == -1:
        #             comma_index = len(filepath[sep_index:])
        #         infered_name = filepath[sep_index:comma_index]
        #         self.polygons_[infered_name] = self.read_files(filepath)
        # elif isinstance(path_files, dict):
        #     for name, filepath in path_files:
        #         self.polygons_[name] = self.read_files(filepath)
        # else:
        #     self.polygons_[path_files] = self.read_files(path_files)
        if isinstance(path_files, str):
            self.read_files(path_files)
        else:
            raise TypeError("For now, SVGPolygoniser works for a signle SVG (with multiple paths) only.")

    def __repr__(self):
        keys = [k for k in self.polygons_.keys()]
        return "Polygoniser(" + str(keys) + ", view_box = " + str(self.view_box_) + ", graph_box = " + \
               str(self.data_box_) + ")"

    def read_files(self, path_file):
        """
        Reads a SVG file and return a list of Polygon composed of the polygons that surround the vectorial path.
        :param path_file: Absolute or relative filepath to the SVG file.
        :return: List of Polygons.
        """
        current_polygon_list = []
        current_points = []
        f = open(path_file, "r")
        svg_tag = False
        read_view_box = None
        path_tag = False
        current_id = None
        read_coord = False
        for line in f:
            if not svg_tag:
                if "<svg" not in line:
                    continue
                else:
                    line = line[line.find("<svg")+4:]
                    svg_tag = True
            if not read_view_box:
                if "viewBox=" not in line:
                    continue
                else:
                    read_view_box = re.search(r"(?<=(viewBox=\"))(\d+ ){3}(\d+)(?=(\"))", line)
                    if read_view_box is not None:
                        line = line[line.find("viewBox")+7:]
                        read_view_box = tuple(map(int, read_view_box.group().split()))
                        if self.view_box_ is None:
                            self.view_box_ = read_view_box
                        elif self.view_box_ != read_view_box:
                            f.close()
                            raise Exception("View Boxes of all path files don't correspond. Found %s ; expected %s"
                                            % (read_view_box, self.view_box_))
            if not path_tag:
                if line.find("<path") != -1:
                    line = line[re.search(r" *<path", line).end():]
                    path_tag = True
                else:
                    continue
            if not current_id:
                id_index = line.find("id=")
                if id_index != -1:
                    current_id = re.search("(?<=(id=\")).*(?=\")", line).group(0)
                    line = line[id_index + 3:]
                else:
                    continue
            if not read_coord:
                if line.find("d=\"") != -1:
                    read_coord = True
                    line = line[line.find("d=\"")+3:]
                else:
                    continue
            skip_next = False  # If the coord is after a "M"
            last_element = None  # To avoid duplicates coords in a row
            for element in line.split():
                if skip_next or element == last_element:
                    skip_next = False
                    continue
                last_element = element
                if element.find("\"M") != -1:
                    skip_next = True
                elif element.startswith("Z"):
                    current_polygon_list.append(mpath.Path(current_points))
                    current_points = []
                elif re.match(r"\d+\.\d+,\d+.\d+", element):
                    current_points.append(self.scale(tuple(map(float, element.split(",")))))
                elif element.find("/>") != -1:
                    self.polygons_[current_id] = current_polygon_list
                    current_polygon_list = []
                    read_coord = False
                    path_tag = False
                    current_id = None

    def findContainer(self, point, in_view_box=False, percent_impute=None):
        """
        Return the name of the polygon which contains the point.
        Warning : it may produce an unpredictable return key if you the files previously fed into the constructor of the
        class showed overlapping paths.
        :param in_view_box: Boolean that tells if the coordinates to be considered are the view_box's original ones.
        :param point: A tuple of of coordinates (x, y)
        :param percent_impute: Percent of the view port that a point should be given a belonging if it is outside of
        all polygons.
        :return: The name of the polygon, or None if the point is outside every polygon.
        """
        if in_view_box:
            point = self.scale(point, reverse=True)
        for k, polygon_list in self.polygons_.items():
            for polygon in polygon_list:
                if polygon.contains_point(point):
                    return k
        if percent_impute is None or percent_impute == 0:
            return None

        # Getting the closest polygon from the point and its closest distance
        min_distance = float("inf")
        closest_polygon = None
        for k, p in self.polygons_.items():
            for polygon in p:
                distance = self.minimal_distance(point, polygon)
                if distance < min_distance:
                    min_distance = distance
                    closest_polygon = k
        # Convert the distance into a percent of the picture's diagonal
        diag = self.get_distance((self.data_box_[0], self.data_box_[1]), (self.data_box_[2], self.data_box_[3]))
        return closest_polygon if min_distance <= percent_impute * diag / 100 else None

    def mapBelongings(self, x_series, y_series, in_view_box=False, percent_impute=None):
        """
        Gets lists of coordinates and return the polygon names to which they belong or None.
        :param x_series: List of x coordinates.
        :param y_series: List of y coordinates.
        :param in_view_box: Boolean that tells if the coordinates to be considered are the view_box's original ones.
        :param percent_impute: If a value is given, the mapper will test diverse positions to find the closest polygon
        up to the value given in percents as a distance relative to the viewport size.
        :return: A list of the polygons names containing each respective point.
        """
        belongings = []
        for i, x in enumerate(x_series):
            belongings.append(self.findContainer((x, y_series[i]), in_view_box, percent_impute))
        return belongings

    def scale(self, point, reverse=False):
        """
        Applies a transformation of a coordinate tuple from a box to another.
        The normal direction of the conversion is from the view_box_ to the data_box_.
        :param point: Tuple of coordinates (x,y)
        :param reverse: If True, inverts the direction of the conversion.
        :return: Coordinates of the point in the new coordinate system.
        """
        if self.data_box_ is None:
            return point
        init_box = self.view_box_ if reverse is False else self.data_box_
        target_box = self.data_box_ if reverse is False else self.view_box_
        if self.invert_y:
            point = (point[0], init_box[3]-point[1])
        if init_box == target_box:
            return point
        return target_box[0] + (point[0] / (init_box[2] - init_box[0]) * (target_box[2] - target_box[0])), \
            target_box[1] + (point[1] / ((init_box[3]) - init_box[1]) * (target_box[3] - target_box[1]))

    @staticmethod
    def minimal_distance(point, path):
        """
        Returns the minimal distance between a point and a polygon.
        :param point: Tuple representing the coordinates (x, y) of the point.
        :param path: Path representing the sides of the polygon.
        :return: The distance between the point and the polygon at the closest projection.
        """
        min_distance = float("inf")
        first_point = None
        a = None
        for segment in path.iter_segments():
            if first_point is None:
                first_point = segment[0]
                a = segment[0]
            else:
                min_distance = min(min_distance, Polygoniser.get_distance_from_segment(point, a, segment[0]))
                a = segment[0]
        return min_distance

    @staticmethod
    def get_distance_from_segment(point, point_a, point_b):
        """
        Returns the distance of a point to the closest point of a segment.
        :param point: Tuple representing the coordinates (x, y) of the point.
        :param point_a: Tuple representing the coordinates (x, y) of the first apex of the segment.
        :param point_b: Tuple representing the coordinates (x, y) of the second apex of the segment.
        :return: The closest point of the segment from the point as a tuple of coordinates (x, y).
        """
        l2 = Polygoniser.get_length_squared(point_a, point_b)
        if l2 == 0:
            return Polygoniser.get_distance(point, point_a)
        return Polygoniser.get_distance(point, Polygoniser.get_projection(point, point_a, point_b))

    @staticmethod
    def get_projection(point, point_a, point_b):
        """
        Returns the projection of a point onto a segment.
        :param point: Tuple representing the coordinates (x, y) of the point.
        :param point_a: Tuple representing the coordinates (x, y) of the first apex of the segment.
        :param point_b: Tuple representing the coordinates (x, y) of the second apex of the segment.
        :return: The coordinates (x, y) of the projection of the point onto the segment.
        """
        t = max(0, min(1, Polygoniser.get_dot_product((point[0] - point_a[0], point[1] - point_a[1]),
                                                      (point_b[0] - point_a[0], point_b[1] - point_a[1]))))
        return point_a[0] + t * (point_b[0] - point_a[0]), point_a[1] + t * (point_b[1] - point_a[1])

    @staticmethod
    def get_length_squared(point_a, point_b):
        """
        Returns the squared distance between a point and another.
        :param point_a: First point as a tuple of coordinates (x, y).
        :param point_b: Second point as a tuple of coordinates (x, y).
        :return: Distance squared between the two points.
        """
        return (point_b[0]-point_a[0])**2 + (point_b[1]-point_a[1])**2

    @staticmethod
    def get_distance(point_a, point_b):
        """
        Returns the distance between two points.
        :param point_a: First point as a tuple of coordinates (x, y).
        :param point_b: Second point as a tuple of coordinates (x, y).
        :return: The distance between the two points.
        """
        return Polygoniser.get_length_squared(point_a, point_b) ** 0.5

    @staticmethod
    def get_dot_product(point_a, point_b):
        """
        Returns the dot product of two points.
        :param point_a: First point as a tuple of coordinates (x, y).
        :param point_b: Second point as a tuple of coordinates (x, y).
        :return: The dot product of the coordinates.
        """
        return point_a[0]*point_b[0]+point_a[1]*point_b[1]
