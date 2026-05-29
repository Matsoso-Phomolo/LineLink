from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedRoom:
    room_number: str
    room_type: str
    sequence_number: int


def generate_room_numbers(
    *,
    total_rooms: int,
    single_rooms: int,
    double_rooms: int,
    single_room_prefix: str,
    double_room_prefix: str,
    starting_room_number: int,
) -> list[GeneratedRoom]:
    if total_rooms <= 0:
        raise ValueError("total_rooms must be greater than 0")

    if single_rooms < 0 or double_rooms < 0:
        raise ValueError("single_rooms and double_rooms cannot be negative")

    if single_rooms + double_rooms != total_rooms:
        raise ValueError("single_rooms + double_rooms must equal total_rooms")

    if single_room_prefix.strip().lower() == double_room_prefix.strip().lower():
        raise ValueError("single and double room prefixes must be different")

    if starting_room_number <= 0:
        raise ValueError("starting_room_number must be greater than 0")

    rooms: list[GeneratedRoom] = []
    current_number = starting_room_number

    for _ in range(single_rooms):
        rooms.append(
            GeneratedRoom(
                room_number=f"{single_room_prefix}-{current_number}",
                room_type="single",
                sequence_number=current_number,
            )
        )
        current_number += 1

    for _ in range(double_rooms):
        rooms.append(
            GeneratedRoom(
                room_number=f"{double_room_prefix}-{current_number}",
                room_type="double",
                sequence_number=current_number,
            )
        )
        current_number += 1

    return rooms
