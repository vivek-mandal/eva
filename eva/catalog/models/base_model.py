# coding=utf-8
# Copyright 2018-2022 EVA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import contextlib

from sqlalchemy import Column, Integer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import create_database, database_exists

from eva.catalog.sql_config import CATALOG_TABLES, SQLConfig
from eva.utils.logging_manager import logger

db_session = SQLConfig().session


class CustomModel:
    """This overrides the default `_declarative_constructor` constructor.

    It skips the attributes that are not present for the model, thus if a
    dict is passed with some unknown attributes for the model on creation,
    it won't complain for `unknown field`s.
    Declares and int `_row_id` field for all tables
    """

    query = db_session.query_property()
    _row_id = Column("_row_id", Integer, primary_key=True)

    def __init__(self, **kwargs):
        cls_ = type(self)
        for k in kwargs:
            if hasattr(cls_, k):
                setattr(self, k, kwargs[k])
            else:
                continue

    def save(self):
        """Add and commit

        Returns: saved object

        """
        try:
            db_session.add(self)
            self._commit()
        except Exception as e:
            db_session.rollback()
            logger.error(f"Database save failed : {str(e)}")
            raise e
        return self

    def update(self, **kwargs):
        """Update and commit

        Args:
            **kwargs: attributes to update

        Returns: updated object

        """
        try:
            for attr, value in kwargs.items():
                if hasattr(self, attr):
                    setattr(self, attr, value)
            return self.save()
        except Exception as e:
            db_session.rollback()
            logger.error(f"Database update failed : {str(e)}")
            raise e

    def delete(self):
        """Delete and commit"""
        try:
            db_session.delete(self)
            self._commit()
        except Exception as e:
            db_session.rollback()
            logger.error(f"Database delete failed : {str(e)}")
            raise e

    def _commit(self):
        """Try to commit. If an error is raised, the session is rollbacked."""
        try:
            db_session.commit()
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database commit failed : {str(e)}")
            raise e


# Custom Base Model to be inherited by all models
BaseModel = declarative_base(cls=CustomModel, constructor=None, bind=SQLConfig().engine)


def init_db():
    """Create database if doesn't exist and create all tables."""
    engine = SQLConfig().engine
    if not database_exists(engine.url):
        logger.info("Database does not exist, creating database.")
        create_database(engine.url)
        logger.info("Creating tables")
        BaseModel.metadata.create_all()


def truncate_catalog_tables():
    """Truncate all the catalog tables"""
    # https://stackoverflow.com/questions/4763472/sqlalchemy-clear-database-content-but-dont-drop-the-schema/5003705#5003705 #noqa
    engine = SQLConfig().engine
    # reflect to refresh the metadata
    BaseModel.metadata.reflect(bind=engine)
    if database_exists(engine.url):
        with contextlib.closing(engine.connect()) as con:
            trans = con.begin()
            for table in reversed(BaseModel.metadata.sorted_tables):
                if table.exists(con):
                    con.execute(table.delete())
            trans.commit()


def drop_all_tables_except_catalog():
    """drop all the tables except the catalog"""
    engine = SQLConfig().engine
    # reflect to refresh the metadata
    BaseModel.metadata.reflect(bind=engine)
    if database_exists(engine.url):
        with contextlib.closing(engine.connect()) as con:
            trans = con.begin()
            for table in reversed(BaseModel.metadata.sorted_tables):
                if table.name not in CATALOG_TABLES:
                    if table.exists(con):
                        table.drop(con)
            trans.commit()
