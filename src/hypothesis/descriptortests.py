"""
Support for testing your custom implementations of descriptors
"""

from hypothesis.strategytable import StrategyTable
from hypothesis.database.converter import ConverterTable
from hypothesis.database import ExampleDatabase
from hypothesis.database.backend import SQLiteBackend
from hypothesis import Verifier, given
from hypothesis.settings import Settings
from unittest import TestCase
from hypothesis.internal.utils.fixers import actually_equal
from hypothesis.internal.utils.hashitanyway import (
    hash_everything, HashItAnyway
)
from random import Random


def descriptor_test_suite(
    descriptor, strategy_table=None, converter_table=None,
    simplify_is_unique=True,
    max_examples=50,
):
    strategy_table = strategy_table or StrategyTable()
    converter_table = converter_table or ConverterTable(strategy_table)
    database = ExampleDatabase(converters=converter_table)
    settings = Settings(
        database=database,
        max_examples=max_examples,
    )
    random = Random()
    verifier = Verifier(
        settings=settings,
        strategy_table=strategy_table,
        random=random
    )
    strategy = strategy_table.strategy(descriptor)
    descriptor_test = given(descriptor, verifier=verifier)

    class ValidationSuite(TestCase):
        @descriptor_test
        def test_can_produce_what_it_produces(self, value):
            assert strategy.could_have_produced(value)

        @descriptor_test
        def test_copying_produces_equality(self, value):
            assert actually_equal(
                value, strategy.copy(value)
            )

        if simplify_is_unique:
            @descriptor_test
            def test_simplify_produces_distinct_results(self, value):
                simpler = list(strategy.simplify(value))
                assert len(set(map(HashItAnyway, simpler))) == len(simpler)

        def test_produces_two_distinct_hashes(self):
            verifier.falsify(
                lambda x, y: hash_everything(x) == hash_everything(y),
                descriptor, descriptor)

        @descriptor_test
        def test_is_not_in_simplify(self, value):
            for simpler in strategy.simplify(value):
                assert not actually_equal(value, simpler)

        @descriptor_test
        def test_can_round_trip_through_the_database(self, value):
            empty_db = ExampleDatabase(
                backend=SQLiteBackend(":memory:"),
                converters=converter_table
            )
            storage = empty_db.storage_for(descriptor)
            storage.save(value)
            values = list(storage.fetch())
            assert len(values) == 1
            assert actually_equal(value, values[0])

        @descriptor_test
        def test_can_minimize_to_empty(self, value):
            simplest = list(strategy.simplify_such_that(
                value, lambda x: True
            ))[-1]
            assert strategy.could_have_produced(simplest)
            assert list(strategy.simplify(simplest)) == []

    return ValidationSuite