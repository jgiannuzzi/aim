from abc import abstractmethod
from typing import Iterator, Dict, Tuple, Type

from aim.sdk.core import type_utils
from aim.sdk.core.query_utils import ContainerQueryProxy, SequenceQueryProxy

from aim.sdk.core.constants import KeyNames

from aim.sdk.core.interfaces.container import ContainerCollection as ABCContainerCollection, ContainerType
from aim.sdk.core.interfaces.sequence import SequenceCollection as ABCSequenceCollection, SequenceType

from aim.storage.query import RestrictedPythonQuery
from aim.storage.context import Context, cached_context

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from aim.sdk.core.container import Container
    from aim.sdk.core.sequence import Sequence
    from aim.storage.treeview import TreeView


class ContainerCollectionBase(ABCContainerCollection[ContainerType]):
    def __init__(self, query_context: Dict):
        self.query_context = query_context
        self.ctype: Type['Container'] = query_context[KeyNames.CONTAINER_TYPE]

    @abstractmethod
    def __iter_meta__(self) -> Iterator[str]:
        ...

    def __iter__(self) -> Iterator['Container']:
        meta_tree = self.query_context['meta_tree']
        storage = self.query_context['storage']
        for hash_ in self.__iter_meta__():
            yield self.ctype.from_storage(storage, meta_tree, hash_=hash_)


class ContainerLimitCollection(ContainerCollectionBase['Container']):
    def __init__(self, base_collection: ContainerCollectionBase['Container'], n: int, query_context):
        super().__init__(query_context)

        self.base_collection = base_collection
        self.limit = n

    def __iter_meta__(self) -> Iterator[str]:
        for i, hash_ in enumerate(self.base_collection.__iter_meta__()):
            if i >= self.limit:
                break
            yield hash_

    def filter(self, expr: str) -> ABCContainerCollection['Container']:
        return ContainerFilterCollection(self, expr, self.query_context)

    def limit(self, n: int) -> ABCContainerCollection['Container']:
        return ContainerLimitCollection(self, n, self.query_context)


class ContainerFilterCollection(ContainerCollectionBase['Container']):
    def __init__(self, base_collection: ContainerCollectionBase['Container'], filter_expr: str, query_context: Dict):
        super().__init__(query_context)

        self.base_collection = base_collection
        self.filter_expr = filter_expr
        self.query = RestrictedPythonQuery(self.filter_expr)

    def __iter_meta__(self) -> Iterator[str]:
        var_name = self.query_context['var_name']
        aliases = (var_name,) if var_name else ()
        alias_names = self.ctype.default_aliases.union(aliases)

        query_cache = self.query_context['query_cache']
        for hash_ in self.base_collection.__iter_meta__():
            cont_tree: 'TreeView' = self.query_context['meta_tree'].subtree('chunks').subtree(hash_)

            proxy = ContainerQueryProxy(cont_tree, query_cache[hash_])
            query_params = {p: proxy for p in alias_names}
            if self.query.check(**query_params):
                yield hash_

    def filter(self, expr: str) -> ABCContainerCollection['Container']:
        return ContainerFilterCollection(self, expr, self.query_context)

    def limit(self, n: int) -> ABCContainerCollection['Container']:
        return ContainerLimitCollection(self, n, self.query_context)


class ContainerCollection(ContainerCollectionBase['Container']):
    def __init__(self, query_context: Dict):
        super().__init__(query_context)

        type_infos = self.query_context[KeyNames.CONTAINER_TYPES_MAP]
        required_typename = self.query_context['required_typename']

        def type_match(hash_) -> bool:
            return type_utils.is_subtype(type_infos.get(hash_, ''), required_typename)

        self.hashes = filter(type_match, self.query_context['storage'].container_hashes())

    def __iter_meta__(self) -> Iterator[str]:
        yield from self.hashes

    def filter(self, expr: str) -> ABCContainerCollection['Container']:
        return ContainerFilterCollection(self, expr, self.query_context)

    def limit(self, n: int) -> ABCContainerCollection['Container']:
        return ContainerLimitCollection(self, n, self.query_context)


class SequenceCollectionBase(ABCSequenceCollection[SequenceType]):
    def __init__(self, query_context: Dict):
        self.query_context = query_context
        self.stype: Type[Sequence] = query_context[KeyNames.SEQUENCE_TYPE]
        self.ctype: Type['Container'] = query_context[KeyNames.CONTAINER_TYPE]
        self._containers: Dict = {}

    @abstractmethod
    def __iter_meta__(self) -> Iterator[Tuple[str, str, int]]:
        ...

    def __iter__(self) -> Iterator['Sequence']:
        meta_tree = self.query_context['meta_tree']
        storage = self.query_context['storage']
        for hash_, name, context in self.__iter_meta__():
            yield self.stype.from_storage(storage, meta_tree, hash_=hash_, name=name, context=context)


class SequenceLimitCollection(SequenceCollectionBase['Sequence']):
    def __init__(self, base_collection: SequenceCollectionBase['Sequence'], n: int, query_context: Dict):
        super().__init__(query_context)

        self.base_collection = base_collection
        self.limit = n

    def __iter_meta__(self) -> Iterator['Sequence']:
        for i, (hash_, name, context) in enumerate(self.base_collection.__iter_meta__()):
            if i >= self.limit:
                break
            yield hash_, name, context

    def filter(self, expr: str) -> ABCSequenceCollection['Sequence']:
        return SequenceFilterCollection(self, expr, self.query_context)

    def limit(self, n: int) -> ABCSequenceCollection['Sequence']:
        return SequenceLimitCollection(self, n, self.query_context)


class SequenceFilterCollection(SequenceCollectionBase['Sequence']):
    def __init__(self, base_collection: SequenceCollectionBase['Sequence'], filter_expr: str, query_context: Dict):
        super().__init__(query_context)

        self.base_collection = base_collection
        self.filter_expr = filter_expr
        self.query = RestrictedPythonQuery(self.filter_expr)

    def __iter_meta__(self) -> Iterator[Tuple[str, str, Dict]]:
        var_name = self.query_context['var_name']
        aliases = (var_name,) if var_name else ()
        alias_names = self.stype.default_aliases.union(aliases)
        container_alias_names = self.ctype.default_aliases

        query_cache = self.query_context['query_cache']
        for hash_, name, ctx_idx in self.base_collection.__iter_meta__():
            cont_tree: 'TreeView' = self.query_context['meta_tree'].subtree('chunks').subtree(hash_)
            seq_tree: 'TreeView' = cont_tree.subtree((KeyNames.SEQUENCES, ctx_idx, name))

            proxy = SequenceQueryProxy(name, self._context_from_idx, ctx_idx, seq_tree, query_cache[hash_])
            c_proxy = ContainerQueryProxy(cont_tree, query_cache[hash_])
            query_params = {p: proxy for p in alias_names}

            query_params.update({cp: c_proxy for cp in container_alias_names})
            if self.query.check(**query_params):
                yield hash_, name, ctx_idx

    @cached_context
    def _context_from_idx(self, ctx_idx) -> Context:
        return Context(self.query_context['meta_tree'][KeyNames.CONTEXTS, ctx_idx])

    def filter(self, expr: str) -> ABCSequenceCollection['Sequence']:
        return SequenceFilterCollection(self, expr, self.query_context)

    def limit(self, n: int) -> ABCSequenceCollection['Sequence']:
        return SequenceLimitCollection(self, n, self.query_context)


class ContainerSequenceCollection(SequenceCollectionBase['Sequence']):
    def __init__(self, hash_, query_context: Dict):
        super().__init__(query_context)

        self.hash = hash_
        self.required_typename = self.query_context['required_typename']
        self.allowed_dtypes = self.query_context[KeyNames.ALLOWED_VALUE_TYPES]

        self._container: Container = None
        self._meta_tree = self.query_context['meta_tree']
        self._sequence_tree = self._meta_tree.subtree('chunks').subtree(hash_).subtree(KeyNames.SEQUENCES)

    def __iter_meta__(self) -> Iterator[Tuple[str, str, Dict]]:
        for context_idx, context_dict in self._sequence_tree.items():
            for name in context_dict.keys():
                item_type = context_dict[name][KeyNames.INFO_PREFIX][KeyNames.VALUE_TYPE]
                sequence_typename = context_dict[name][KeyNames.INFO_PREFIX][KeyNames.SEQUENCE_TYPE]
                if type_utils.is_subtype(sequence_typename, self.required_typename) and \
                   type_utils.is_allowed_type(item_type, self.allowed_dtypes):
                    yield self.hash, name, context_idx

    def filter(self, expr: str) -> ABCSequenceCollection['Sequence']:
        return SequenceFilterCollection(self, expr, self.query_context)

    def limit(self, n: int) -> ABCSequenceCollection['Sequence']:
        return SequenceLimitCollection(self, n, self.query_context)


class SequenceCollection(SequenceCollectionBase['Sequence']):
    def __init__(self, query_context: Dict):
        super().__init__(query_context)
        self.hashes = self.query_context['storage'].container_hashes()

    def __iter_meta__(self) -> Iterator[Tuple[str, str, Dict]]:
        for hash_ in self.hashes:
            coll = ContainerSequenceCollection(hash_, self.query_context)
            yield from coll.__iter_meta__()

    def filter(self, expr: str) -> ABCSequenceCollection['Sequence']:
        return SequenceFilterCollection(self, expr, self.query_context)

    def limit(self, n: int) -> ABCSequenceCollection['Sequence']:
        return SequenceLimitCollection(self, n, self.query_context)
