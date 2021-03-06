import cudarray as ca
from ...base import ParamMixin
from ...parameter import Parameter
from ..base import Unary


class Linear(Unary, ParamMixin):
    def __init__(self, n_out, weights):
        self.n_out = n_out
        self.weights = Parameter.from_any(weights)

    def __call__(self, x):
        super(Linear, self).__call__(x)
        self.bpropable = True
        return self

    def setup(self):
        x_shape = self.x.out_shape
        self.out_shape = (x_shape[0], self.n_out)
        self.out = ca.empty(self.out_shape)
        self.out_grad = ca.empty(self.out_shape)
        self.weights.setup((x_shape[1], self.n_out))

    def fprop(self):
        ca.dot(self.x.out, self.weights.array, out=self.out)

    def bprop(self):
        ca.dot(self.x.out.T, self.out_grad, out=self.weights.grad_array)
        ca.dot(self.out_grad, self.weights.array.T, out=self.x.out_grad)

    @property
    def params(self):
        return self.weights,

    @params.setter
    def params(self, params):
        self.weights, = params


class Affine(Unary, ParamMixin):
    def __init__(self, n_out, weights, bias=0.0):
        self.n_out = n_out
        self.weights = Parameter.from_any(weights)
        self.bias = Parameter.from_any(bias)

    def __call__(self, x):
        super(Affine, self).__call__(x)
        self.bpropable = True
        return self

    def setup(self):
        x_shape = self.x.out_shape
        self.out_shape = (x_shape[0], self.n_out)
        self.out = ca.empty(self.out_shape)
        self.out_grad = ca.empty(self.out_shape)
        self.weights.setup((x_shape[1], self.n_out))
        self.bias.setup(self.n_out)

    def fprop(self):
        ca.dot(self.x.out, self.weights.array, out=self.out)
        self.out += self.bias.array

    def bprop(self):
        ca.dot(self.x.out.T, self.out_grad, out=self.weights.grad_array)
        ca.sum(self.out_grad, axis=0, out=self.bias.grad_array)
        ca.dot(self.out_grad, self.weights.array.T, out=self.x.out_grad)

    @property
    def params(self):
        return self.weights, self.bias

    @params.setter
    def params(self, params):
        self.weights, self.bias = params


class OneHot(Unary):
    def __init__(self, n_classes):
        self.n_classes = n_classes

    def setup(self):
        self.out_shape = self.x.out_shape + (self.n_classes,)
        self.out = ca.empty(self.out_shape)

    def fprop(self):
        ca.nnet.one_hot_encode(self.x.out, self.n_classes, self.out)
