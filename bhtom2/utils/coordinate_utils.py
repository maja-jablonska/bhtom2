from astropy.coordinates import Angle, SkyCoord
import astropy.units as u
from bhtom_base.bhtom_targets.models import Target

from bhtom2.utils.bhtom_logger import BHTOMLogger

logger: BHTOMLogger = BHTOMLogger(__name__, '[Coordinate Utils]')


def fill_galactic_coordinates(target: Target) -> Target:
    """
    Automatically calculate galactic coordinates for a target
    (if they aren't already filled in), using ra and dec
    @param target: Observation target
    @return: Observation target (changed in-place)
    """

    # If at least one of ra and dec is unfilled, return without changing
    # (there is nothing to calculate basing on)
    if not target.ra or not target.dec:
        return target

    # If the galactic coordinates are filled in, return without changing
    if target.galactic_lat and target.galactic_lng:
        return target

    coordinates: SkyCoord = SkyCoord(ra=target.ra,
                                     dec=Angle(target.dec, unit=u.deg).wrap_at('90d').degree,
                                     unit='deg')
    target.galactic_lat = coordinates.galactic.b.degree
    target.galactic_lng = coordinates.galactic.l.degree

    logger.debug(f'Filling in galactic coordinates for target {target.name}...')

    return target
