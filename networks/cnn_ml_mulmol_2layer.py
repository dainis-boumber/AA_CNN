import tensorflow as tf
import numpy as np


class TextCNN(object):
    """
    two-layer-convolution that works with multi-modality
    2d slider on first convolution, then padded to same length for another convolution.
    the first c currently have relu but not pooled, generating 220 * 300 features per sentence
    the second c have relu then pooled to generates 300 feature for fully connected output
    """
    batch_size = None

    def __init__(
            self, sequence_length, num_classes,
            word_vocab_size, embedding_size, filter_sizes, num_filters,
            pref2_vocab_size, pref3_vocab_size, suff2_vocab_size, suff3_vocab_size, pos_vocab_size,
            l2_reg_lambda=0.0, init_embedding=None):
        # Placeholders for input, output and dropout, First None is batch size.
        self.input_x = tf.placeholder(tf.int32, [self.batch_size, sequence_length], name="input_x")

        self.input_pref2 = tf.placeholder(tf.int32, [self.batch_size, sequence_length], name="input_pref2")
        self.input_pref3 = tf.placeholder(tf.int32, [self.batch_size, sequence_length], name="input_pref3")
        self.input_suff2 = tf.placeholder(tf.int32, [self.batch_size, sequence_length], name="input_suff2")
        self.input_suff3 = tf.placeholder(tf.int32, [self.batch_size, sequence_length], name="input_suff3")
        self.input_pos = tf.placeholder(tf.int32, [self.batch_size, sequence_length], name="input_pos")

        self.input_y = tf.placeholder(tf.float32, [self.batch_size, num_classes], name="input_y")
        self.dropout_keep_prob = tf.placeholder(tf.float32, name="dropout_keep_prob")

        # Keeping track of l2 regularization loss (optional)
        l2_loss = tf.constant(0.0)

        # Embedding layer
        with tf.device('/cpu:0'), tf.name_scope("embedding"):
            if init_embedding is None:
                W = tf.Variable(
                    tf.random_uniform([word_vocab_size, embedding_size], -1.0, 1.0),
                    name="W")
            else:
                W = tf.Variable(init_embedding, name="W", dtype="float32")
            self.embedded_chars = tf.nn.embedding_lookup(W, self.input_x)
            self.embedded_chars_expanded = tf.expand_dims(self.embedded_chars, -1)

            W_pref2 = tf.Variable(tf.random_uniform([pref2_vocab_size, embedding_size], -1.0, 1.0), name="W_pref2")
            self.embedded_chars_pref2 = tf.nn.embedding_lookup(W_pref2, self.input_pref2)
            self.embedded_chars_expanded_pref2 = tf.expand_dims(self.embedded_chars_pref2, -1)
            print(("embedded_chars_expanded_pref2: " + str(self.embedded_chars_expanded_pref2.get_shape())))

            W_pref3 = tf.Variable(tf.random_uniform([pref3_vocab_size, embedding_size], -1.0, 1.0), name="W_pref3")
            self.embedded_chars_pref3 = tf.nn.embedding_lookup(W_pref3, self.input_pref3)
            self.embedded_chars_expanded_pref3 = tf.expand_dims(self.embedded_chars_pref3, -1)
            print(("embedded_chars_expanded_pref3: " + str(self.embedded_chars_expanded_pref3.get_shape())))

            W_suff2 = tf.Variable(tf.random_uniform([suff2_vocab_size, embedding_size], -1.0, 1.0), name="W_suff2")
            self.embedded_chars_suff2 = tf.nn.embedding_lookup(W_suff2, self.input_suff2)
            self.embedded_chars_expanded_suff2 = tf.expand_dims(self.embedded_chars_suff2, -1)
            print(("embedded_chars_expanded_suff2: " + str(self.embedded_chars_expanded_suff2.get_shape())))

            W_suff3 = tf.Variable(tf.random_uniform([suff3_vocab_size, embedding_size], -1.0, 1.0), name="W_suff3")
            self.embedded_chars_suff3 = tf.nn.embedding_lookup(W_suff3, self.input_suff3)
            self.embedded_chars_expanded_suff3 = tf.expand_dims(self.embedded_chars_suff3, -1)
            print(("embedded_chars_expanded_suff3: " + str(self.embedded_chars_expanded_suff3.get_shape())))

            W_pos = tf.Variable(tf.random_uniform([pos_vocab_size, embedding_size], -1.0, 1.0), name="W_pos")
            self.embedded_chars_pos = tf.nn.embedding_lookup(W_pos, self.input_pos)
            self.embedded_chars_expanded_pos = tf.expand_dims(self.embedded_chars_pos, -1)
            print(("embedded_chars_expanded_pos: " + str(self.embedded_chars_expanded_pos.get_shape())))

            self.whole_emb = tf.concat(values=[self.embedded_chars_expanded,
                                               self.embedded_chars_expanded_pref2,
                                               self.embedded_chars_expanded_pref3,
                                               self.embedded_chars_expanded_suff2,
                                               self.embedded_chars_expanded_suff3,
                                               self.embedded_chars_expanded_pos],
                                       axis=3)

        # Create a convolution + maxpool layer for each filter size
        first_pooled_outputs = []
        for i, filter_size in enumerate(filter_sizes):
            with tf.name_scope("conv-1-%s" % filter_size):
                # Convolution Layer
                filter_shape = [filter_size, embedding_size, 6, num_filters]
                W = tf.Variable(tf.truncated_normal(filter_shape, stddev=0.1), name="W")
                b = tf.Variable(tf.constant(0.1, shape=[num_filters]), name="b")
                conv = tf.nn.conv2d(
                    self.whole_emb,
                    W,
                    strides=[1, 1, 1, 1],
                    padding="VALID",
                    name="conv_word")
                # conv ==> [?, sequence_length - filter_size + 1, 1, 100]
                top_pad = int((filter_size - 1) / 2.0)
                bottom_pad = filter_size - 1 - top_pad
                conv = tf.pad(conv, [[0, 0], [top_pad, bottom_pad], [0, 0], [0, 0]], mode='CONSTANT', name="conv_word_pad")
                conv = tf.reshape(conv, [-1, sequence_length, num_filters])
                # Apply nonlinearity
                h = tf.nn.relu(tf.nn.bias_add(conv, b), name="relu")
                first_pooled_outputs.append(h)

        num_filters_total = num_filters * len(filter_sizes)
        first_pooled_outputs = tf.concat(values=first_pooled_outputs, axis=2)
        first_pooled_outputs = tf.expand_dims(first_pooled_outputs, -1)
        print(("first_pooled_outputs: " + str(first_pooled_outputs.get_shape())))

        conv_2_pooled_outputs = []
        for i, filter_size in enumerate(filter_sizes):
            with tf.name_scope("conv-2-maxpool-%s" % filter_size):
                # Convolution Layer
                filter_shape = [filter_size, num_filters_total, 1, num_filters]
                W = tf.Variable(tf.truncated_normal(filter_shape, stddev=0.1), name="W")
                b = tf.Variable(tf.constant(0.1, shape=[num_filters]), name="b")
                conv = tf.nn.conv2d(
                    first_pooled_outputs,
                    W,
                    strides=[1, 1, 1, 1],
                    padding="VALID",
                    name="conv_2")
                # conv ==> [?, 218, 1, 100]
                # Apply nonlinearity
                h = tf.nn.relu(tf.nn.bias_add(conv, b), name="relu")
                # Maxpooling over the outputs
                pooled = tf.nn.max_pool(
                    h,
                    ksize=[1, sequence_length - filter_size + 1, 1, 1],
                    strides=[1, 1, 1, 1],
                    padding='VALID',
                    name="pool")
                conv_2_pooled_outputs.append(pooled)

        # Combine all the pooled features
        self.h_pool = tf.concat(conv_2_pooled_outputs, 3)
        self.h_pool_flat = tf.reshape(self.h_pool, [-1, num_filters_total])

        # Add dropout
        with tf.name_scope("dropout-keep" + str(0.5)):
            self.h_drop = tf.nn.dropout(self.h_pool_flat, self.dropout_keep_prob)



        # Final (unnormalized) scores and predictions
        with tf.name_scope("output"):
            # W = tf.Variable(tf.truncated_normal([num_filters_total, num_classes], stddev=0.1), name="W")
            W = tf.get_variable(
                "W",
                shape=[num_filters_total, num_classes],
                initializer=tf.contrib.layers.xavier_initializer())
            b = tf.Variable(tf.constant(0.1, shape=[num_classes]), name="b")
            l2_loss += tf.nn.l2_loss(W)
            # l2_loss += tf.nn.l2_loss(b)
            self.scores = tf.nn.xw_plus_b(self.h_drop, W, b, name="scores")
            self.predictions = tf.sigmoid(self.scores, name="predictions")
            print(("Prediction shape: " + str(self.predictions.get_shape())))

        # self.rate_percentage = [0.0] * num_classes
        # with tf.name_scope("prediction-ratio"):
        #     for i in range(num_classes):
        #         rate_allrow_logistic = tf.equal(self.predictions, i)
        #         rate_logistic = tf.reduce_all(rate_allrow_logistic, axis=1)
        #         self.rate_percentage[i] = tf.reduce_mean(tf.cast(rate_logistic, "float"),
        #                                                  name="rate-" + str(i) + "/percentage")

        # CalculateMean cross-entropy loss
        with tf.name_scope("loss-lbd" + str(l2_reg_lambda)):
            losses = tf.nn.sigmoid_cross_entropy_with_logits(self.scores, self.input_y)
            self.loss = tf.reduce_mean(losses) + l2_reg_lambda * l2_loss

        # Accuracy
        with tf.name_scope("accuracy"):
            # all correct
            correct_predictions = tf.equal(tf.greater_equal(self.predictions, 0.5), tf.equal(self.input_y, 1))
            correct_predictions = tf.reduce_all(correct_predictions, axis=1)
            self.accuracy = tf.reduce_mean(tf.cast(correct_predictions, "float"), name="accuracy")
