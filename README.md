# EvaDB AI-SQL Database System

<div>
        <a href="https://colab.research.google.com/github/georgia-tech-db/eva/blob/master/tutorials/03-emotion-analysis.ipynb">
            <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open EvaDB on Colab"/>
        </a>
        <a href="https://join.slack.com/t/eva-db/shared_invite/zt-1i10zyddy-PlJ4iawLdurDv~aIAq90Dg">
            <img alt="Slack" src="https://img.shields.io/badge/slack-evadb-ff69b4.svg?logo=slack">
        </a>          
        <a href="https://twitter.com/evadb_ai">
            <img alt="Twitter" src="https://img.shields.io/badge/twitter-evadb-bde1ee.svg?logo=twitter">
        </a>  
        <a href="https://github.com/orgs/georgia-tech-db/projects/3">
            <img src="https://img.shields.io/badge/evadb-roadmap-a6c096" alt="Roadmap"/>
        </a>
        <img alt="PyPI" src="https://img.shields.io/pypi/v/evadb.svg"/>
        <img alt="License" src="https://img.shields.io/badge/license-Apache%202-brightgreen.svg?logo=apache"/>
        <img alt="Coverage Status" src="https://coveralls.io/repos/github/georgia-tech-db/eva/badge.svg?branch=master"/>     
        <a href="https://pepy.tech/project/evadb">
          <img alt="Downloads" src="https://static.pepy.tech/badge/evadb/month"/>
        </a>
        <img alt="Python Versions" src="https://img.shields.io/badge/Python--versions-3.8%20|%203.9%20|%203.10-brightgreen"/>       
</div>

<p align="center"> <b><h3>EvaDB is a database system for building simpler and faster AI-powered applications.</b></h3> </p>

EvaDB is an AI-SQL database system for developing applications powered by AI models. We aim to simplify the development and deployment of AI-powered applications that operate on structured (tables, feature stores) and unstructured data (text documents, videos, PDFs, podcasts, etc.).

EvaDB accelerates AI pipelines by 10x using a collection of performance optimizations inspired by time-tested SQL database systems, including data-parallel query execution, function caching, sampling, and cost-based predicate reordering. EvaDB supports an AI-oriented query language tailored for analyzing both structured and unstructured data. It has first-class support for PyTorch, Hugging Face, YOLO, and Open AI models.

The high-level Python and SQL APIs allows even beginners to use EvaDB in a few lines of code. Advanced users can define custom user-defined functions that wrap around any AI model or Python library. EvaDB is fully implemented in Python and licensed under the Apache license.

## Quick Links

- [Features](#features)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Roadmap](https://github.com/orgs/georgia-tech-db/projects/3)
- [Architecture Diagram](#architecture-diagram)
- [Illustrative Applications](#illustrative-applications)
- [Screenshots](#screenshots)
- [Community and Support](#community-and-support)
- [Twitter](https://twitter.com/evadb_ai)
- [Contributing](#contributing)
- [License](#license)

## Features

- 🔮 Build simpler AI-powered applications using short Python or SQL queries
- ⚡️ 10x faster applications using AI-centric query optimization  
- 💰 Save money spent on GPUs
- 🚀 First-class support for your custom deep learning models through user-defined functions
- 📦 Built-in caching to eliminate redundant model invocations across queries
- ⌨️ First-class support for PyTorch, Hugging Face, YOLO, and Open AI models
- 🐍 Installable via pip and fully implemented in Python

## Illustrative Applications

Here are some illustrative EvaDB-powered applications (each Jupyter notebook can be opened on Google Colab):

 * 🔮 <a href="https://evadb.readthedocs.io/en/stable/source/tutorials/11-similarity-search-for-motif-mining.html">Reddit Image Similarity Search</a>
 * 🔮 <a href="https://evadb.readthedocs.io/en/stable/source/tutorials/08-chatgpt.html">ChatGPT-based video question answering</a>
 * 🔮 <a href="https://evadb.readthedocs.io/en/stable/source/tutorials/12-query-pdf.html">Querying PDF documents</a>
 * 🔮 <a href="https://evadb.readthedocs.io/en/stable/source/tutorials/02-object-detection.html">Analysing traffic flow with YOLO</a>
 * 🔮 <a href="https://evadb.readthedocs.io/en/stable/source/tutorials/03-emotion-analysis.html">Examining emotion palette of a movie</a>
 * 🔮 <a href="https://evadb.readthedocs.io/en/stable/source/tutorials/07-object-segmentation-huggingface.html">Image segmentation with Hugging Face</a>
 * 🔮 <a href="https://github.com/georgia-tech-db/license-plate-recognition">Recognizing license plates</a>
 * 🔮 <a href="https://github.com/georgia-tech-db/toxicity-classification">Analysing toxicity of social media memes </a>

## Documentation

* [Detailed Documentation](https://evadb.readthedocs.io/)
  - The <a href="https://evadb.readthedocs.io/en/stable/source/overview/installation.html">Getting Started</a> page shows how you can use EvaDB for different AI tasks and how you can easily extend EvaDB to support your custom deep learning model through user-defined functions.
  - The <a href="https://evadb.readthedocs.io/en/latest/source/tutorials/11-similarity-search-for-motif-mining.html">User Guides</a> section contains Jupyter Notebooks that demonstrate how to use various features of EvaDB. Each notebook includes a link to Google Colab, where you can run the code yourself.
* [Tutorials](https://github.com/georgia-tech-db/eva/blob/master/tutorials/03-emotion-analysis.ipynb)
* [Join us on Slack](https://join.slack.com/t/eva-db/shared_invite/zt-1i10zyddy-PlJ4iawLdurDv~aIAq90Dg)
* [Follow us on Twitter](https://twitter.com/evadb_ai)
* [Medium-Term Roadmap](https://github.com/orgs/georgia-tech-db/projects/3)
* [Demo](https://evadb.readthedocs.io/en/stable/source/tutorials/08-chatgpt.html)

## Quick Start

- Step 1: Install EvaDB using pip. EvaDB supports Python versions >= `3.8`:

```shell
pip install evadb
```

- Step 2: Write your AI app!

```python
import evadb

# Grab a EvaDB cursor to load data and run queries
cursor = evadb.connect().cursor()

# Load a collection of news videos into the 'news_videos' table
# This command returns a Pandas Dataframe with the query's output
# In this case, the output indicates the number of loaded videos
cursor.load(
    file_regex="news_videos/*.mp4",
    format="VIDEO",
    table_name="news_videos"
).df()

# Define a function that wraps around a speech-to-text (Whisper) model
# Such functions are known as user-defined functions or UDFs
# So, we are creating a Whisper UDF here
# After creating the UDF, we can use the function in any query
cursor.create_udf(
    udf_name="SpeechRecognizer",
    type="HuggingFace",
    task='automatic-speech-recognition',
    model='openai/whisper-base'
).df()

# EvaDB automatically extract the audio from the video
# We only need to run the SpeechRecongizer UDF on the 'audio' column
# to get the transcript and persist it in a table called 'transcripts'
cursor.query(
    """CREATE TABLE transcripts AS
       SELECT SpeechRecognizer(audio) from news_videos;"""
).df()

# We next incrementally construct the ChatGPT query using EvaDB's Python API
# The query is based on the 'transcripts' table
# This table has a column called 'text' with the transcript text
query = cursor.table('transcripts')

# Since ChatGPT is a built-in function, we don't have to define it
# We can just directly use it in the query
# We need to set the OPENAI_KEY as an environment variable
os.environ["OPENAI_KEY"] = OPENAI_KEY
query = query.select("ChatGPT('Is this video summary related to LLMs', text)")

# Finally, we run the query to get the results as a dataframe
response = query.df()
```

- **Write functions to wrap around your custom deep learning models**

```python
# Define a function that wraps around a speech-to-text (Whisper) model
# Such functions are known as user-defined functions or UDFs
# So, we are creating a Whisper UDF here
# After creating the UDF, we can use the function in any query
cursor.create_udf(
    udf_name="SpeechRecognizer",
    type="HuggingFace",
    task='automatic-speech-recognition',
    model='openai/whisper-base'
).df()
```

- **Chain multiple models in a single query to set up useful AI pipelines**

```python
# Analyse emotions of actors in an Interstellar movie clip using PyTorch models
query = cursor.table("Interstellar")
# Get faces using a `FaceDetector` function
query = query.cross_apply("UNNEST(FaceDetector(data))", "Face(bounding_box, confidence)")
# Focus only on frames 100 through 200 in the clip
query = query.filter("id > 100 AND id < 200")
# Get the emotions of the detected faces using a `EmotionDetector` function
query = query.select("id, bbox, EmotionDetector(Crop(data, bounding_box))")

# Run the query and get the query result as a dataframe
response = query.df()
```

- **EvaDB runs queries faster using its AI-centric query optimizer**. Two key optimizations are:

   💾 **Caching**: EvaDB automatically caches and reuses previous query results (especially model inference results), eliminating redundant computation and reducing query processing time.

   🎯 **Predicate Reordering**: EvaDB optimizes the order in which the query predicates are evaluated (e.g., runs the faster, more selective model first), leading to faster queries and lower inference costs.

```mysql
  -- Query 1: Find all images of black-colored dogs
  SELECT id, bbox FROM dogs 
  JOIN LATERAL UNNEST(Yolo(data)) AS Obj(label, bbox, score) 
  WHERE Obj.label = 'dog' 
    AND Color(Crop(data, bbox)) = 'black'; 

  -- Query 2: Find all Great Danes that are black-colored
  SELECT id, bbox FROM dogs 
  JOIN LATERAL UNNEST(Yolo(data)) AS Obj(label, bbox, score) 
  WHERE Obj.label = 'dog' 
    AND DogBreedClassifier(Crop(data, bbox)) = 'great dane' 
    AND Color(Crop(data, bbox)) = 'black';
```

By reusing the results of the first query and reordering the predicates based on the available cached inference results, EvaDB runs the second query **10x faster**!

## Architecture Diagram

This diagram presents the key components of EvaDB. EvaDB's AI-centric Query Optimizer takes a parsed query as input and generates a query plan that is then executed by the Query Engine. The Query Engine hits multiple storage engines to retrieve the data required for efficiently running the query:
1. Structured data (SQL database system connected via `sqlalchemy`).
2. Unstructured media data (on cloud buckets or local filesystem).
3. Vector data (vector database system).

<img width="700" alt="Architecture Diagram" src="https://github.com/georgia-tech-db/eva/assets/5521975/01452ec9-87d9-4d27-90b2-c0b1ab29b16c">

## Screenshots

### 🔮 [Traffic Analysis](https://evadb.readthedocs.io/en/stable/source/tutorials/02-object-detection.html) (Object Detection Model)
| Source Video  | Query Result |
|---------------|--------------|
|<img alt="Source Video" src="https://github.com/georgia-tech-db/eva/releases/download/v0.1.0/traffic-input.webp" width="300"> |<img alt="Query Result" src="https://github.com/georgia-tech-db/eva/releases/download/v0.1.0/traffic-output.webp" width="300"> |

### 🔮 [PDF Question Answering](https://evadb.readthedocs.io/en/stable/source/tutorials/12-query-pdf.html) (Question Answering Model)

| App |
|-----|
|<img alt="Source Video" src="https://github.com/georgia-tech-db/eva/releases/download/v0.1.0/pdf-qa.webp" width="400"> |

### 🔮 [MNIST Digit Recognition](https://evadb.readthedocs.io/en/stable/source/tutorials/01-mnist.html) (Image Classification Model)
| Source Video  | Query Result |
|---------------|--------------|
|<img alt="Source Video" src="https://github.com/georgia-tech-db/eva/releases/download/v0.1.0/mnist-input.webp" width="150"> |<img alt="Query Result" src="https://github.com/georgia-tech-db/eva/releases/download/v0.1.0/mnist-output.webp" width="150"> |

### 🔮 [Movie Emotion Analysis](https://evadb.readthedocs.io/en/stable/source/tutorials/03-emotion-analysis.html) (Face Detection + Emotion Classification Models)

| Source Video  | Query Result |
|---------------|--------------|
|<img alt="Source Video" src="https://github.com/georgia-tech-db/eva/releases/download/v0.1.0/gangubai-input.webp" width="400"> |<img alt="Query Result" src="https://github.com/georgia-tech-db/eva/releases/download/v0.1.0/gangubai-output.webp" width="400"> |

### 🔮 [License Plate Recognition](https://github.com/georgia-tech-db/eva-application-template) (Plate Detection + OCR Extraction Models)

| Query Result |
|--------------|
<img alt="Query Result" src="https://github.com/georgia-tech-db/license-plate-recognition/blob/main/README_files/README_12_3.png" width="300"> |

## Community and Support

👋 If you have general questions about EvaDB, want to say hello or just follow along, we'd like to invite you to join our [Slack Community](https://join.slack.com/t/eva-db/shared_invite/zt-1i10zyddy-PlJ4iawLdurDv~aIAq90Dg) and to [follow us on Twitter](https://twitter.com/evadb_ai).

<a href="https://join.slack.com/t/eva-db/shared_invite/zt-1i10zyddy-PlJ4iawLdurDv~aIAq90Dg">              
    <img src="https://raw.githubusercontent.com/georgia-tech-db/eva/master/docs/images/eva/eva-slack.png" alt="EvaDB Slack Channel" width="500">
</a>

If you run into any problems or issues, please create a Github issue and we'll try our best to help.

Don't see a feature in the list? Search our issue tracker if someone has already requested it and add a comment to it explaining your use-case, or open a new issue if not. We prioritize our [roadmap](https://github.com/orgs/georgia-tech-db/projects/3) based on user feedback, so we'd love to hear from you.

## Contributing

[![PyPI Version](https://img.shields.io/pypi/v/evadb.svg)](https://pypi.org/project/evadb)
[![CI Status](https://circleci.com/gh/georgia-tech-db/eva.svg?style=svg)](https://circleci.com/gh/georgia-tech-db/eva)
[![Documentation Status](https://readthedocs.org/projects/evadb/badge/?version=latest)](https://evadb.readthedocs.io/en/latest/index.html)

EvaDB is the beneficiary of many [contributors](https://github.com/georgia-tech-db/eva/graphs/contributors). All kinds of contributions to EvaDB are appreciated. To file a bug or to request a feature, please use <a href="https://github.com/georgia-tech-db/eva/issues">GitHub issues</a>. <a href="https://github.com/georgia-tech-db/eva/pulls">Pull requests</a> are welcome.

For more information, see our
[contribution guide](https://evadb.readthedocs.io/en/stable/source/contribute/index.html).

## License
Copyright (c) 2018-present [Georgia Tech Database Group](http://db.cc.gatech.edu/).
Licensed under [Apache License](LICENSE).
