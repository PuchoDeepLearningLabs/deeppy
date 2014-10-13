#!/usr/bin/env python
# coding: utf-8

import os
import numpy as np
import sklearn.datasets
import deeppy as dp


def run():
    # Fetch data
    mnist = sklearn.datasets.fetch_mldata('MNIST original', data_home='./data')

    X = mnist.data.astype(dp.float_)/255.0-0.5
    X = np.reshape(X, (-1, 1, 28, 28))
    y = mnist.target.astype(dp.int_)
    n = y.size
    shuffle_idxs = np.random.random_integers(0, n-1, n)
    X = X[shuffle_idxs, ...]
    y = y[shuffle_idxs, ...]

    n_test = 10000
    n_valid = 10000
    n_train = n - n_test - n_valid
    X_train = X[:n_train]
    y_train = y[:n_train]
    X_valid = X[n_train:n_train+n_valid]
    y_valid = y[n_train:n_train+n_valid]
    X_test = X[n_train+n_valid:]
    y_test = y[n_train+n_valid:]

    n_classes = np.unique(y_train).size

    # Setup neural network
    nn = dp.NeuralNetwork(
        layers=[
            dp.Convolutional(
                n_filters=20,
                filter_shape=(5, 5),
                weights=dp.NormalFiller(sigma=0.01),
                weight_decay=0.00001,
            ),
            dp.Activation('relu'),
            dp.Pool(
                win_shape=(2, 2),
                strides=(2, 2),
                method='max',
            ),
            dp.Convolutional(
                n_filters=50,
                filter_shape=(5, 5),
                weights=dp.NormalFiller(sigma=0.01),
                weight_decay=0.00001,
            ),
            dp.Activation('relu'),
            dp.Pool(
                win_shape=(2, 2),
                strides=(2, 2),
                method='max',
            ),
            dp.Flatten(),
            dp.FullyConnected(
                n_output=500,
                weights=dp.NormalFiller(sigma=0.01),
            ),
            dp.FullyConnected(
                n_output=n_classes,
                weights=dp.NormalFiller(sigma=0.01),
            ),
            dp.MultinomialLogReg(),
        ],
    )

    # Train neural network
    def valid_error_fun():
        return nn.error(X_valid, y_valid)
    trainer = dp.StochasticGradientDescent(
        batch_size=128, learn_rate=0.1, learn_momentum=0.9, max_epochs=15
    )
    trainer.train(nn, X_train, y_train, valid_error_fun)

    # Visualize convolutional filters to disk
    for layer_idx, layer in enumerate(nn.layers):
        if not isinstance(layer, dp.Convolutional):
            continue
        W = np.array(layer.params()[0].values)
        dp.misc.img_save(dp.misc.conv_filter_tile(W),
                         os.path.join('mnist',
                                      'convnet_layer_%i.png' % layer_idx))

    # Evaluate on test data
    error = nn.error(X_test, y_test)
    print('Test error rate: %.4f' % error)


if __name__ == '__main__':
    run()
