(function($) {
	$(function() {

		var filters = $(".classes-filter");
		filters.on("click", "a", function(e) {
			var clickedOption, filterName, newFilterValue, newFilterLabel;

			clickedOption = $(e.target);

			filterName = clickedOption.closest(".classes-filter").attr("data-filtername");
			if (filterName == "") {
				throw new Error("No filter name supplied");
			}

			newFilterValue = clickedOption.attr("data-filtervalue");
			if (newFilterValue == "") {
				throw new Error("No filter value in selected option");
			}

			newFilterLabel = clickedOption.text();
			if (newFilterLabel == "") {
				throw new Error("No filter label in selected option");
			}

			setFilter(filterName, newFilterValue, newFilterLabel);

			// TODO:WV:20170515:Update classes list via a suitable method
		});
	});

	function getFilterValue(filterName) {
		var filter, value;

		filter = getFilter(filterName);
		value = filter.find(".selected-item").attr("data-filtervalue");

		return value;
	}

	function setFilter(filterName, newValue, newLabel) {
		var filter;

		filter = getFilter(filterName);
		filter.find(".selected-item").attr("data-filtervalue", newValue).text(newLabel);
	}

	function getFilter(filterName) {
		var filter;

		filter = $(".classes-filter").filter(function() {
			return ($(this).attr("data-filtername") == filterName);
		});

		return filter;
	}

})(jQuery);