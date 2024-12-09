"""
An API wrapping SortedStringTrie from pytrie (see https://github.com/gsakkis/pytrie)
"""
from itertools import islice

from pytrie import SortedStringTrie, SortedTrie


#: A dictionary containing node data, where the key is the curie and the value is a
#: dictionary containing the node data. The dictionary should contain the keys "name" and
#: "definition" and optionally "synonyms".
NodeData = dict[str, dict[str, str]]
#: A tuple containing the match name, name, curie, and definition of a node
Entry = tuple[str, str, str, str]
#: A dictionary containing the trie index to initialize the NodesTrie instance with
TrieIndex = dict[str, Entry]


class NodesTrie(SortedStringTrie):
    """A Trie structure that has case-insensitive search methods"""

    def case_insensitive_search(self, prefix: str, top_n: int = 100) -> list[Entry]:
        """Get case-insensitive matches with the given prefix

        Parameters
        ----------
        prefix :
            The prefix to search for.
        top_n :
            The maximum number of matches to return. Default: 100

        Returns
        -------
        :
            A list of all case-insensitive matches with the given prefix
        """
        prefix = prefix.lower()
        return list(islice(self.values(prefix), top_n))


class CappedTrie(SortedTrie):
    """A Trie structure that caps the number of results returned

    This subclass is used only to cap the number of results returned by the trie.
    It does not modify the search behavior like `NodesTrie`.
    """

    def search(self, prefix, top_n: int = 100) -> list[str]:
        """Get the top N results from the trie

        Parameters
        ----------
        prefix :
            The prefix to search for.
        top_n :
            The maximum number of results to return. Default: 100.

        Returns
        -------
        :
            The top N results from the trie
        """
        return list(islice(self.values(prefix), top_n))
