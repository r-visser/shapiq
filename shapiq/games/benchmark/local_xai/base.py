"""This module contains all tabular machine learning games."""

from typing import Callable, Optional, Union

import numpy as np

from shapiq.games.base import Game
from shapiq.games.imputer import MarginalImputer


class LocalExplanation(Game):
    """The LocalExplanation game class.

    The `LocalExplanation` game is a game that performs local explanation of a model at a specific
    data point as a coalition game. The game evaluates the model's prediction on feature subsets
    around a specific data point. Therein, marginal imputation is used to impute the missing values
    of the data point (for more information see `MarginalImputer`).

    Args:
        x: The data point to explain. Can be an index of the background data or a 1d matrix of shape
             (n_features). Defaults to `None` which will select a random data point from the
             background data.
        data: The background data used to fit the imputer. Should be a 2d matrix of shape
            (n_samples, n_features).
        model: The model to explain as a callable function expecting data points as input and
            returning the model's predictions. The input should be a 2d matrix of shape
            (n_samples, n_features) and the output a 1d matrix of shape (n_samples).
        random_state: The random state to use for the imputer. Defaults to `None`.
        normalize: A flag to normalize the game values. If `True`, then the game values are
            normalized and centered to be zero for the empty set of features. Defaults to `True`.

    Attributes:
        x: The data point to explain.
        empty_prediction: The model's prediction on an empty data point (all features missing).

    Examples:
        >>> from sklearn.tree import DecisionTreeRegressor
        >>> from sklearn.datasets import make_regression
        >>> from shapiq.games.benchmark.local_xai import LocalExplanation
        >>> # create a regression dataset and fit the model
        >>> x_data, y_data = make_regression(n_samples=100, n_features=10, noise=0.1)
        >>> model = DecisionTreeRegressor(max_depth=4)
        >>> model.fit(x_data, y_data)
        >>> # create a LocalExplanation game
        >>> x_explain = x_data[0]
        >>> game = LocalExplanation(x=x_explain, data=x_data, model=model.predict)
        >>> # evaluate the game on a specific coalition
        >>> coalition = np.zeros(shape=(1, 10), dtype=bool)
        >>> coalition[0][0, 1, 2] = True
        >>> value = game(coalition)
        >>> # precompute the game (if needed)
        >>> game.precompute()
        >>> # save and load the game
        >>> game.save("game.pkl")
        >>> new_game = LocalExplanation.load("game.pkl")
        >>> # save and load the game values
        >>> game.save_values("values.npz")
        >>> from shapiq.games import Game
        >>> new_game_from_values = Game(path_to_values="values.npz")
    """

    def __init__(
        self,
        *,
        data: np.ndarray,
        model: Callable[[np.ndarray], np.ndarray],
        x: Union[np.ndarray, int] = None,
        imputer: Optional[MarginalImputer] = None,
        random_state: Optional[int] = None,
        normalize: bool = True,
    ) -> None:

        # get x_explain
        self.x = x if x is not None else _get_x_explain(x, data)

        # init the imputer which serves as the workhorse of this Game
        self._imputer = imputer
        if self._imputer is None:
            self._imputer = MarginalImputer(
                model=model,
                data=data,
                x=self.x,
                random_state=random_state,
                normalize=False,
            )

        self.empty_prediction: float = self._imputer.empty_prediction

        # init the base game
        super().__init__(
            data.shape[1],
            normalize=normalize,
            normalization_value=self._imputer.empty_prediction,
        )

    def value_function(self, coalitions: np.ndarray) -> np.ndarray:
        """Calls the model and returns the prediction.

        Args:
            coalitions: The coalitions as a one-hot matrix for which the game is to be evaluated.

        Returns:
            The output of the model on feature subsets.
        """
        return self._imputer(coalitions)


def _get_x_explain(x: Optional[Union[np.ndarray, int]], x_set: np.ndarray) -> np.ndarray:
    """Returns the data point to explain given the input.

    Args:
        x: The data point to explain. Can be an index of the background data or a 1d matrix of shape
            (n_features).
        x_set: The data set to select the data point from. Should be a 2d matrix of shape
            (n_samples, n_features).

    Returns:
        The data point to explain as a numpy array.
    """
    if x is None:
        x = x_set[np.random.randint(0, x_set.shape[0])]
    if isinstance(x, int):
        x = x_set[x]
    return x