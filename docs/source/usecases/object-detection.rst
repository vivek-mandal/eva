.. _object-detection:

Object Detection
================

.. raw:: html

    <embed>
    <table align="left">
    <td>
        <a target="_blank" href="https://colab.research.google.com/github/georgia-tech-db/eva/blob/staging/tutorials/02-object-detection.ipynb"><img src="https://www.tensorflow.org/images/colab_logo_32px.png" /> Run on Google Colab</a>
    </td>
    <td>
        <a target="_blank" href="https://github.com/georgia-tech-db/eva/blob/staging/tutorials/02-object-detection.ipynb"><img src="https://www.tensorflow.org/images/GitHub-Mark-32px.png" /> View source on GitHub</a>
    </td>
    <td>
        <a target="_blank" href="https://github.com/georgia-tech-db/eva/raw/staging/tutorials/02-object-detection.ipynb"><img src="https://www.tensorflow.org/images/download_logo_32px.png" /> Download notebook</a>
    </td>
    </table><br><br>
    </embed>

Introduction
------------

In this tutorial, we present how to use ``YOLO`` models in EvaDB to detect objects. In particular, we focus on detecting objects from the challenging, real-world ``UA-DETRAC`` dataset. EvaDB makes it easy to do object detection using its built-in support for ``YOLO`` models.

In this tutorial, besides detecting objects, we will also showcase a query where the model's output is used to retrieve a subset of frames with ``pedestrian`` and ``car`` objects.

.. include:: ../shared/evadb.rst

We will assume that the input ``UA-DETRAC`` video is loaded into ``EvaDB``. To download the video and load it into ``EvaDB``, see the complete `object detection notebook on Colab <https://colab.research.google.com/github/georgia-tech-db/eva/blob/master/tutorials/02-object-detection.ipynb>`_.

Create Object Detection Function
--------------------------------

To create a custom ``Yolo`` function based on the popular ``YOLO-v8m`` model, use the ``CREATE FUNCTION`` statement. In this query, we leverage EvaDB's built-in support for ``ultralytics`` models. We only need to specify the ``model`` parameter in the query to create this function:

.. code-block:: sql

        CREATE UDF IF NOT EXISTS Yolo
        TYPE  ultralytics
        MODEL 'yolov8m.pt';

Object Detection Queries
------------------------

After the function is registered in ``EvaDB``, you can use it subsequent SQL queries in different ways. 

In the following query, we call the object detector on every image in the video. The output of the function is stored in the ``label`` column (i.e., the digit associated with the given frame) of the output ``DataFrame``.

.. code-block:: sql

    SELECT id, Yolo(data) 
    FROM ObjectDetectionVideos
    WHERE id < 20
    LIMIT 5;

This query returns the label of all the images:

.. code-block:: 

    +-----------------------------------------------------------------------------------------------------+
    | objectdetectionvideos.id              | yolo.labels                                                |
    +--------------------------+-----------------------------------------------------------------+
    | 0                        | [car, car, car, car, car, car, person, car, ...             |
    | 1                        | [car, car, car, car, car, car, car, car, car, ...             |
    +-----------------------------------------------------------------------------------------------------+

Filtering Based on YOLO Function
--------------------------------

In the following query, we use the output of the object detector to retrieve a subset of frames that contain a ``pedestrian`` and a ``car``.

.. code-block:: sql

    SELECT id
        FROM ObjectDetectionVideos 
        WHERE ['pedestrian', 'car'] <@ Yolo(data).label;

Now, the ``DataFrame`` only contains frames with the desired objects:

.. code-block:: 

    +------------------------------+
    |  objectdetectionvideos.label |
    |------------------------------|
    |                            6 |
    |                            6 |
    +------------------------------+

.. include:: ../shared/footer.rst
