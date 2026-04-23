from abc import ABC, abstractmethod


class BasePrompt(ABC):
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        pass

    @property
    @abstractmethod
    def user_prompt(self) -> str:
        pass

    def get_messages(self, **kwargs) -> list:
        return [
            ("system", self.system_prompt),
            ("user", self.user_prompt.format(**kwargs)),
        ]
