"""Evidence numbering and room labelling.

EVIDNUM is a text column. Ordering by it put "9" after "10", so from
the tenth item onward the form pre-filled a number already in use --
and EVIDNUM is unique, so the save then failed with nothing on screen
to explain why.
"""

import pytest

from models import Evidence, Rooms, get_session
import utils


def _add_evidence(*numbers):
    with get_session() as session:
        for number in numbers:
            session.add(
                Evidence(
                    EVIDNUM=str(number),
                    EVIDQTY="1",
                    EVIDDESC=f"item {number}",
                    EVIDLOCROOM="Room A",
                    EVIDLOCROOMDETAIL="shelf",
                    EVIDFOUNDBY="Doe, John",
                    EVIDFOUNDBYWITNESS="Roe, Jane",
                )
            )


def _add_rooms(*labels):
    with get_session() as session:
        for label in labels:
            session.add(
                Rooms(
                    ROOMLABEL=label,
                    ROOMDESC=f"Room {label}",
                    ROOMFIRSTAGENT="Doe, John",
                    ROOMSECONDAGENT="Roe, Jane",
                )
            )


# ----- evidence numbering -----

def test_first_item_is_one():
    assert utils.get_next_evid_num() == "1"


def test_counts_up_within_single_digits():
    _add_evidence(1, 2, 3)
    assert utils.get_next_evid_num() == "4"


def test_does_not_collapse_at_ten():
    """The regression: text ordering made "9" the highest of 1..11."""
    _add_evidence(*range(1, 12))
    assert utils.get_next_evid_num() == "12"


def test_survives_three_digits():
    _add_evidence(*range(1, 101))
    assert utils.get_next_evid_num() == "101"


def test_suggested_number_is_actually_free(populated):
    """The suggestion must be saveable -- it used to hit UNIQUE."""
    suggested = utils.get_next_evid_num()
    _add_evidence(suggested)
    with get_session() as session:
        assert session.query(Evidence).filter_by(
            EVIDNUM=suggested).count() == 1


def test_hand_entered_suffix_does_not_reset_the_count():
    """A "12A" is skipped, not treated as unparseable-so-start-again."""
    _add_evidence(*range(1, 13))
    _add_evidence("12A")
    assert utils.get_next_evid_num() == "13"


def test_only_non_numeric_values_start_from_one():
    _add_evidence("A1", "B2")
    assert utils.get_next_evid_num() == "1"


# ----- room labels -----

def test_first_room_is_a():
    assert utils.get_next_room_ltr() == "A"


def test_rooms_advance_through_the_alphabet():
    _add_rooms("A", "B", "C")
    assert utils.get_next_room_ltr() == "D"


def test_room_after_z_is_aa():
    """chr(ord("Z") + 1) produced "[" -- not a room label."""
    import string
    _add_rooms(*string.ascii_uppercase)
    assert utils.get_next_room_ltr() == "AA"


def test_room_label_reuses_a_gap():
    """Deleting room B should let the next room take B again."""
    _add_rooms("A", "C")
    assert utils.get_next_room_ltr() == "B"


@pytest.mark.parametrize(
    "position,expected",
    [(1, "A"), (26, "Z"), (27, "AA"), (52, "AZ"), (53, "BA"), (702, "ZZ")],
)
def test_label_for_position(position, expected):
    assert utils.label_for_position(position) == expected
