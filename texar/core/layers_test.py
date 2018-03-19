#
"""
Unit tests for various layers.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import tensorflow as tf
import tensorflow.contrib.rnn as rnn

import texar as tx
from texar import context
from texar.hyperparams import HParams
from texar.core import layers

# pylint: disable=no-member, protected-access

class GetRNNCellTest(tf.test.TestCase):
    """Tests RNN cell creator.
    """

    def test_get_rnn_cell(self):
        """Tests :func:`texar.core.layers.get_rnn_cell`.
        """
        emb_dim = 4
        num_units = 64

        hparams = {
            "cell": {
                "type": rnn.BasicLSTMCell(num_units)
            }
        }
        cell = layers.get_rnn_cell(hparams)
        self.assertTrue(isinstance(cell, rnn.BasicLSTMCell))

        hparams = {
            "cell": {
                "type": "tensorflow.contrib.rnn.GRUCell",
                "kwargs": {
                    "num_units": num_units
                }
            },
            "num_layers": 2,
            "dropout": {
                "input_keep_prob": 0.8,
                "variational_recurrent": True,
                "input_size": [emb_dim, num_units]
            },
            "residual": True,
            "highway": True
        }

        hparams_ = HParams(hparams, layers.default_rnn_cell_hparams())
        cell = layers.get_rnn_cell(hparams_)

        batch_size = 16
        inputs = tf.zeros([batch_size, emb_dim], dtype=tf.float32)
        output, state = cell(inputs,
                             cell.zero_state(batch_size, dtype=tf.float32))
        with self.test_session() as sess:
            sess.run(tf.global_variables_initializer())
            output_, state_ = sess.run([output, state],
                                       feed_dict={context.is_train(): True})
            self.assertEqual(output_.shape[0], batch_size)
            if isinstance(state_, (list, tuple)):
                self.assertEqual(state_[0].shape[0], batch_size)
                self.assertEqual(state_[0].shape[1],
                                 hparams_.cell.kwargs.num_units)
            else:
                self.assertEqual(state_.shape[0], batch_size)
                self.assertEqual(state_.shape[1],
                                 hparams_.cell.kwargs.num_units)


class GetLayerTest(tf.test.TestCase):
    """Tests layer creator.
    """
    def test_get_layer(self):
        """Tests :func:`texar.core.layers.get_layer`.
        """
        hparams = {
            "type": "Conv1D"
        }
        layer = layers.get_layer(hparams)
        self.assertTrue(isinstance(layer, tf.layers.Conv1D))

        hparams = {
            "type": "MergeLayer",
            "kwargs": {
                "layers": [
                    {"type": "Conv1D"},
                    {"type": "Conv1D"}
                ]
            }
        }
        layer = layers.get_layer(hparams)
        self.assertTrue(isinstance(layer, tx.core.MergeLayer))


class MergeLayerTest(tf.test.TestCase):
    """Tests MergeLayer.
    """

    def test_output_shape(self):
        """Tests MergeLayer.compute_output_shape function.
        """
        input_shapes = [[None, 1, 2], [64, 2, 2], [None, 3, 2]]

        concat_layer = layers.MergeLayer(mode='concat', axis=1)
        concat_output_shape = concat_layer.compute_output_shape(input_shapes)
        self.assertEqual(concat_output_shape, [64, 6, 2])

        sum_layer = layers.MergeLayer(mode='sum', axis=1)
        sum_output_shape = sum_layer.compute_output_shape(input_shapes)
        self.assertEqual(sum_output_shape, [64, 2])

        input_shapes = [[None, 5, 2], [64, None, 2], [2]]
        esum_layer = layers.MergeLayer(mode='elemwise_sum')
        esum_output_shape = esum_layer.compute_output_shape(input_shapes)
        self.assertEqual(esum_output_shape, [64, 5, 2])

    def test_layer_logics(self):
        """Test the logic of MergeLayer.
        """
        layers_ = []
        layers_.append(tf.layers.Conv1D(filters=200, kernel_size=3))
        layers_.append(tf.layers.Conv1D(filters=200, kernel_size=4))
        layers_.append(tf.layers.Conv1D(filters=200, kernel_size=5))
        layers_.append(tf.layers.Dense(200))
        layers_.append(tf.layers.Dense(200))
        m_layer = layers.MergeLayer(layers_)

        inputs = tf.zeros([64, 16, 1024], dtype=tf.float32)
        outputs = m_layer(inputs)
        with self.test_session() as sess:
            sess.run(tf.global_variables_initializer())
            outputs_ = sess.run(outputs)
            self.assertEqual(outputs_.shape[0], 64)
            self.assertEqual(outputs_.shape[2], 200)
            self.assertEqual(
                outputs_.shape,
                m_layer.compute_output_shape(inputs.shape.as_list()))

    def test_trainable_variables(self):
        """Test the trainable_variables of the layer.
        """
        layers_ = []
        layers_.append(tf.layers.Conv1D(filters=200, kernel_size=3))
        layers_.append(tf.layers.Conv1D(filters=200, kernel_size=4))
        layers_.append(tf.layers.Conv1D(filters=200, kernel_size=5))
        layers_.append(tf.layers.Dense(200))
        layers_.append(tf.layers.Dense(200))
        m_layer = layers.MergeLayer(layers_)

        inputs = tf.zeros([64, 16, 1024], dtype=tf.float32)
        _ = m_layer(inputs)

        num_vars = sum([len(layer.trainable_variables) for layer in layers_])
        self.assertEqual(num_vars, len(m_layer.trainable_variables))

class SequentialLayerTest(tf.test.TestCase):
    """Tests sequential layer.
    """

    def test_seq_layer(self):
        """Test sequential layer.
        """
        layers_ = []
        layers_.append(tf.layers.Dense(100))
        layers_.append(tf.layers.Dense(200))
        seq_layer = layers.SequentialLayer(layers_)

        output_shape = seq_layer.compute_output_shape([None, 10])
        self.assertEqual(output_shape[1].value, 200)

        inputs = tf.zeros([10, 20], dtype=tf.float32)
        outputs = seq_layer(inputs)

        num_vars = sum([len(layer.trainable_variables) for layer in layers_])
        self.assertEqual(num_vars, len(seq_layer.trainable_variables))

        with self.test_session() as sess:
            sess.run(tf.global_variables_initializer())
            outputs_ = sess.run(outputs)
            self.assertEqual(outputs_.shape[0], 10)
            self.assertEqual(outputs_.shape[1], 200)


if __name__ == "__main__":
    tf.test.main()
