(function($) {
	$(function() {

		// Set filters on page load
		// TODO:WV:20170515:Could do this in page template
		var urlParts = location.pathname.split("/");
		var filters = ["dates", "ages"];
		var urlPartOffset = 2;
		for (var i in filters) {
			i = parseInt(i);
			if (typeof urlParts[urlPartOffset + i] != "undefined") {
				setFilter(filters[i], urlParts[urlPartOffset + i]);
			}
		}

		// Set filters when changed
		var filters = $(".classes-filter");
		filters.on("click", "a", function(e) {
			var clickedOption, filterName, newFilterValue;

			clickedOption = $(e.target);

			filterName = clickedOption.closest(".classes-filter").attr("data-filtername");
			if (filterName == "") {
				throw new Error("No filter name supplied");
			}

			newFilterValue = clickedOption.attr("data-filtervalue");
			if (newFilterValue == "") {
				throw new Error("No filter value in selected option");
			}

			setFilter(filterName, newFilterValue);

			// Update list
			// TODO:WV:20170515:Use AJAX + history API if possible
			location.pathname = "/classes/"+getFilterValue("dates")+"/"+getFilterValue("ages");
		});
	});

	function getFilterValue(filterName) {
		var filter, value;

		filter = getFilter(filterName);
		value = filter.find(".selected-item").attr("data-filtervalue");

		return value;
	}

	function setFilter(filterName, newValue) {
		var filter, item, newLabel;

		filter = getFilter(filterName);

		item = filter.find("a").filter(function() {
			return ($(this).attr("data-filtervalue") == newValue);
		});
		if (item.length == 0) {
			return;
		}
		newLabel = item.text();

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