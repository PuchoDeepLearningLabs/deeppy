import cudarray as ca
from ..base import CollectionMixin
from . import digraph
from .base import (
    Expr, Constant, NoBPropMixin, NoFPropMixin, SplitMixin, Output
)


# TODO: find better name (Split is too similar to numpy.vsplit)
class Split(Expr, SplitMixin):
    def __init__(self, n_splits):
        if n_splits <= 1:
            raise ValueError('n_splits should be >1')
        self.n_splits = n_splits

    def __call__(self, x):
        self.x = x
        self.inputs = [x]
        self.outputs = [Output()(self) for i in range(self.n_splits)]
        self.bpropable = x.bpropable
        return self.outputs

    def setup(self):
        out_shape = self.x.out_shape
        for i in range(self.n_splits):
            self.outputs[i].out_shape = out_shape
            self.outputs[i].out = self.x.out
            self.outputs[i].bpropable = self.bpropable
            if self.bpropable:
                self.outputs[i].out_grad = ca.zeros(out_shape)

    def fprop(self):
        for i in range(self.n_splits):
            self.outputs[i].out = self.x.out

    def bprop(self):
        ca.copyto(self.x.out_grad, self.outputs[0].out_grad)
        for i in range(1, self.n_splits):
            self.x.out_grad += self.outputs[i].out_grad


def expr_graph(expr):
    graph = digraph.DiGraph()
    nodes = set([expr])
    seen = set(nodes)
    while nodes:
        node = nodes.pop()
        for neighbor in node.inputs:
            if isinstance(neighbor, (Constant)):
                continue
            graph.add_edge(neighbor, node)
            if neighbor not in seen:
                nodes.add(neighbor)
                seen.add(neighbor)
    return graph


class ExprGraph(CollectionMixin):
    def __init__(self, expr):
        self.expr = expr
        self._initialized = False
        self._fprop_top = None
        self._bprop_top = None
        self.graph = None

    def setup(self):
        # Build graph
        graph = expr_graph(self.expr)

        # Insert Split nodes
        for node, out_degree in graph.out_degree():
            if out_degree <= 1 or out_degree - len(node.inputs) == 0 or \
               not node.bpropable or isinstance(node, SplitMixin):
                continue
            split = Split(out_degree)
            split_exprs = split(node)
            for i, (_, in_node) in enumerate(list(graph.edges([node]))):
                graph.remove_edge(node, in_node)
                new_inputs = [split_exprs[i] if n is node else n
                              for n in in_node.inputs]
                in_node(*new_inputs)
                graph.add_edge(split, split_exprs[i])
                graph.add_edge(split_exprs[i], in_node)
            graph.add_edge(node, split)

        # Prepare fprop and bprop orderings
        fprop_top = digraph.topsort(graph)
        for node in fprop_top:
            node.setup()

        # We need to rebuild graph because setup() may change the graph to
        # facilitate broadcasting operations
        # TODO: figure out if this should be disallowed
        graph = expr_graph(self.expr)
        fprop_top = digraph.topsort(graph)

        fprop_top = [n for n in fprop_top if not isinstance(n, NoFPropMixin)]

        graph_rev = digraph.reverse(graph)
        bprop_top = digraph.topsort(graph_rev)
        bprop_top = [n for n in bprop_top
                     if n.bpropable and not isinstance(n, NoBPropMixin)]

        self.graph = graph
        self._fprop_top = fprop_top
        self._bprop_top = bprop_top
        self.out_shape = self._fprop_top[-1].out_shape
        self._initialized = True

    @property
    def collection(self):
        return self.graph.nodes()

    def fprop(self):
        for node in self._fprop_top:
            node.fprop()
        self.out = self._fprop_top[-1].out

    def bprop(self):
        self._bprop_top[0].out_grad = self.out_grad
        for node in self._bprop_top:
            node.bprop()
