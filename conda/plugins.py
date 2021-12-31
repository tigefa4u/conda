from collections.abc import Iterable
from typing import Callable, List, NamedTuple, Optional, Tuple

import pluggy


_hookspec = pluggy.HookspecMarker('conda')
hookimp = pluggy.HookimplMarker('conda')


class CondaSubcommand(NamedTuple):
    """Conda subcommand entry.

    :param name: Subcommand name (as-in ``conda my-subcommand-name``).
    :param summary: Subcommand summary, will be shown in ``conda --help``.
    :param action: Callable that will be run when the subcommand is invoked.
    """
    name: str
    summary: str
    action: Callable[
        [List[str]],  # arguments
        Optional[int],  # return code
    ]


@_hookspec
def conda_cli_register_subcommands() -> Iterable[CondaSubcommand]:
    """Register external subcommands in Conda.

    :return: An iterable of subcommand entries.
    """
