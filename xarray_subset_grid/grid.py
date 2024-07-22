from abc import ABC, abstractmethod
from collections.abc import Iterable

import numpy as np
import xarray as xr


class Grid(ABC):
    """Abstract class for grid types"""

    @staticmethod
    @abstractmethod
    def recognize(ds: xr.Dataset) -> bool:
        """Recognize if the dataset matches the given grid"""
        return False

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the grid type"""
        return "grid"

    @abstractmethod
    def grid_vars(self, ds: xr.Dataset) -> list[str]:
        """List of grid variables

        These variables are used to define the grid and thus should be kept
        when subsetting the dataset
        """
        return set()

    @abstractmethod
    def data_vars(self, ds: xr.Dataset) -> set[str]:
        """List of data variables

        These variables exist on the grid and are available to used for
        data analysis. These can be discarded when subsetting the dataset
        when they are not needed.
        """
        return set()

    def extra_vars(self, ds: xr.Dataset) -> set[str]:
        """List of variables that are not grid vars or data vars.

        These variables area ll the ones in the dataset that are not used
        to specify the grid, nor data on the grid.
        """
        return set(ds.data_vars) - self.data_vars(ds) - self.grid_vars(ds)

    def subset_vars(self, ds: xr.Dataset, vars: Iterable[str]) -> xr.Dataset:
        """Subset the dataset to the given variables, keeping the grid variables as well"""
        subset = list(self.grid_vars(ds)) + list(vars)
        return ds[subset]

    def has_vertical_levels(self, ds: xr.Dataset) -> bool:
        """Check if the dataset has vertical coordinates"""
        return ds.cf.coordinates.get("vertical", None) is not None

    def subset_vertical_level(
        self, ds: xr.Dataset, level: float, method: str | None = None
    ) -> xr.Dataset:
        """Subset the dataset to the vertical level

        :param ds: The dataset to subset
        :param level: The vertical level to subset to
        :param method: The method to use for the selection, this is the
            same as the method in xarray.Dataset.sel
        """
        if not self.has_vertical_levels(ds):
            return ds

        vertical_coords = ds.cf.coordinates["vertical"]
        if all([i in ds.indexes for i in vertical_coords]):
            selection = {coord: level for coord in vertical_coords}
            return ds.sel(selection, method=method)
        else:
            # Otherwise, the vertical coordinates are not indexible, so we have to find the
            # closest levels manually, then slice the dataset using the found level
            selections = {}
            for coord in vertical_coords:
                elevation_index = int(np.absolute(ds[coord] - level).argmin().values)
                selections[coord] = elevation_index
            return ds.isel(selections)

    def subset_vertical_levels(
        self, ds: xr.Dataset, levels: tuple[float, float], method: str | None = None
    ) -> xr.Dataset:
        """Subset the dataset to the vertical level

        :param ds: The dataset to subset
        :param levels: The vertical levels to subset to. This is a tuple
            with the minimum and maximum level. The minimum must be smaller
            than the maximum.
        :param method: The method to use for the selection, this is the
            same as the method in xarray.Dataset.sel
        """
        if not self.has_vertical_levels(ds):
            return ds

        if levels[0] >= levels[1]:
            raise ValueError("The minimum level must be smaller than the maximum level")

        vertical_coords = ds.cf.coordinates["vertical"]
        if all([i in ds.indexes for i in vertical_coords]):
            selection = {coord: slice(levels[0], levels[1]) for coord in vertical_coords}
            return ds.sel(selection, method=method)
        else:
            # Otherwise, the vertical coordinates are not indexible, so we have to find the
            # closest levels manually, then slice the dataset using the found levels
            selections = {}
            for coord in vertical_coords:
                da_elevations = ds[coord]
                elevation_indexes = [
                    int(np.absolute(da_elevations - level).argmin().values) for level in levels
                ]
                selections[coord] = slice(*elevation_indexes)
            return ds.isel(selections)

    @abstractmethod
    def subset_polygon(
        self, ds: xr.Dataset, polygon: list[tuple[float, float]] | np.ndarray
    ) -> xr.Dataset:
        """Subset the dataset to the grid
        :param ds: The dataset to subset
        :param polygon: The polygon to subset to
        :return: The subsetted dataset
        """
        return ds

    def subset_bbox(self, ds: xr.Dataset, bbox: tuple[float, float, float, float]) -> xr.Dataset:
        """Subset the dataset to the bounding box
        :param ds: The dataset to subset
        :param bbox: The bounding box to subset to
        :return: The subsetted dataset
        """
        polygon = np.array(
            [
                [bbox[0], bbox[3]],
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
            ]
        )
        return self.subset_polygon(ds, polygon)
