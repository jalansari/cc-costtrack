from cc_costtrack import CostTrackError


class TestCostTrackError:
    def test_prefix_applied(self):
        err = CostTrackError("something went wrong")
        assert str(err) == "cc-costtrack: something went wrong"

    def test_is_exception(self):
        assert issubclass(CostTrackError, Exception)


# TODO - complete tests
