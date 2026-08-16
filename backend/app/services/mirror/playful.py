from app.models.entities import MirrorInterest


_BOUNDARY = (
    "Entertainment only — no psychological interpretation and never Happiness DNA evidence."
)


def _activity(
    interest: MirrorInterest,
    *,
    title: str,
    question: str,
    options: list[str],
    interaction: str,
    answer: str | None = None,
) -> dict:
    payload = {
        "interest_id": interest.id,
        "category": interest.category,
        "interest": interest.name,
        "title": title,
        "question": question,
        "options": options,
        "interaction": interaction,
        "purpose": interest.purpose,
        "dna_allowed": interest.dna_allowed,
        "note": _BOUNDARY,
    }
    if answer is not None:
        payload["answer"] = answer
    return payload


def build_playful_activity(interest: MirrorInterest) -> dict:
    """Build a deterministic game without calling an AI or inference service."""

    name = interest.name.strip()
    lower_name = name.casefold()
    category = interest.category.casefold()

    if "game of thrones" in lower_name or "throne" in lower_name:
        answer = "Winter is Coming"
        return _activity(
            interest,
            title="Your GOT house-words challenge",
            question="Which house words belong to House Stark?",
            options=[answer, "Fire and Blood", "Hear Me Roar"],
            answer=answer,
            interaction="quiz",
        )

    if "angry birds" in lower_name or "angry bird" in lower_name:
        answer = "High arc"
        return _activity(
            interest,
            title="Angry Birds wall-shot mini-game",
            question=(
                "A pig's tower is hiding behind a tall wall. Which launch is most "
                "likely to clear it?"
            ),
            options=["Low skim", "Medium launch", answer],
            answer=answer,
            interaction="mini_game",
        )

    if "cricket" in lower_name:
        answer = "Find the gap, then run hard"
        return _activity(
            interest,
            title="Cricket final-over dash",
            question=(
                "Your team needs 7 runs from 3 balls. Which mini-plan keeps the "
                "chase alive?"
            ),
            options=[answer, "Block all three", "Walk off for snacks"],
            answer=answer,
            interaction="mini_game",
        )

    if category == "series":
        return _activity(
            interest,
            title=f"A 20-second {name} challenge",
            question=f"Pick a spoiler-free way to make a friend guess {name}.",
            options=["Act an entrance", "Give a one-line plot clue", "Sketch a symbol"],
            interaction="playful_choice",
        )

    if category == "game":
        return _activity(
            interest,
            title=f"Build a bonus level for {name}",
            question="Which ridiculous twist should the next level add?",
            options=["Reverse gravity", "Tiny boss, huge hat", "Everything bounces"],
            interaction="playful_choice",
        )

    if category == "sport":
        return _activity(
            interest,
            title=f"Your {name} commentator sprint",
            question="The clock is nearly out. Pick the call for one last play.",
            options=["All eyes on this!", "Here comes the twist!", "One more chance!"],
            interaction="playful_choice",
        )

    return _activity(
        interest,
        title=f"A tiny {name} remix",
        question=f"Choose a 30-second just-for-fun challenge inspired by {name}.",
        options=["Speed round", "Silly constraint", "Teach one move"],
        interaction="playful_choice",
    )
