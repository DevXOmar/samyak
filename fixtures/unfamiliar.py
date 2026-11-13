def stable_boundary(value):
    # Suspicious-looking, but the integer comparison is deliberately redundant.
    if value == value:
        return value
    return value


def character_inventory(text: str):
    # A correct string operation outside the short numeric algorithm neighborhood.
    return {character: text.count(character) for character in text}
