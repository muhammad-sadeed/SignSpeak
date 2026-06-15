class WordAssembler:
    """
    Converts per-frame ASL letter predictions into words and sentences.

    - Deduplicates repeated letter predictions (min_consecutive_frames threshold)
    - Allows double letters via a per-letter cooldown (same_letter_cooldown_frames)
    - Detects word boundaries when the hand is absent for word_cooldown_frames
    - Exposes: current_letter, current_word, sentence for on-screen display
    """

    def __init__(
        self,
        word_cooldown_frames=45,
        min_consecutive_frames=5,
        same_letter_cooldown_frames=10,
    ):
        self.word_cooldown_frames = word_cooldown_frames
        self.min_consecutive_frames = min_consecutive_frames
        self.same_letter_cooldown_frames = same_letter_cooldown_frames

        self.current_letter = None
        self.current_word = ""
        self.sentence = ""

        self._candidate_letter = None
        self._candidate_frames = 0
        self._hand_gone_frames = 0
        self._committed_letter = None
        self._committed_frames_ago = 0

    def update(self, letter: str | None):
        if letter is None:
            self._candidate_frames = 0
            self._committed_frames_ago += 1
            self._hand_gone_frames += 1

            if self._hand_gone_frames >= self.word_cooldown_frames:
                self._finalize_word()
            return

        self._hand_gone_frames = 0

        if letter == self._candidate_letter:
            self._candidate_frames += 1
        else:
            self._candidate_frames = 1
            self._candidate_letter = letter

        if letter != self._committed_letter:
            self._committed_frames_ago += 1
        # else: holding same letter — don't advance cooldown

        if self._candidate_frames >= self.min_consecutive_frames:
            same_as_committed = letter == self._committed_letter
            cooldown_expired = self._committed_frames_ago >= self.same_letter_cooldown_frames

            if not same_as_committed or cooldown_expired:
                should_add = (
                    cooldown_expired  # force re-add for double letters
                    or letter != self.current_letter
                )
                if should_add:
                    if self.current_letter is not None:
                        self.current_word += self.current_letter
                    self.current_letter = letter
                    self._committed_letter = letter
                    self._committed_frames_ago = 0

    def _finalize_word(self):
        if self.current_letter is not None:
            self.current_word += self.current_letter
            self.current_letter = None

        if self.current_word:
            if self.sentence:
                self.sentence += " " + self.current_word
            else:
                self.sentence = self.current_word
            self.current_word = ""

        self._candidate_letter = None
        self._candidate_frames = 0
        self._hand_gone_frames = 0
        self._committed_letter = None
        self._committed_frames_ago = 0

    def undo(self):
        """Remove the last letter that was committed or is pending."""
        if self.current_letter is not None:
            self.current_letter = None
        elif self.current_word:
            self.current_word = self.current_word[:-1]
        self._candidate_letter = None
        self._candidate_frames = 0
        self._committed_letter = None
        self._committed_frames_ago = 0

    def reset(self):
        self.current_letter = None
        self.current_word = ""
        self.sentence = ""
        self._candidate_letter = None
        self._candidate_frames = 0
        self._hand_gone_frames = 0
        self._committed_letter = None
        self._committed_frames_ago = 0
