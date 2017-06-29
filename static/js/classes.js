
/*
 * Filters
 */
(function($) {
	$(function() {
		var filters, queryStringParts, i, queryStringData, urlParts, category;

		// Set up default options in filters on page load
		filters = $(".classes-filter");
		filters.each(function() {
			var filter, defaultValue, defaultLabel;

			filter = $(this);

			defaultValue = filter.attr("data-defaultvalue");
			defaultLabel = filter.attr("data-defaultlabel");

			filter.find(".default-option").attr("data-filtervalue", defaultValue).text(defaultLabel);
		});

		// Set filters on page load
		queryStringParts, i, queryStringData
		queryStringParts = location.search.split(/[?=&]/).slice(1);
		queryStringData = {};
		for (i in queryStringParts) {
			i = parseInt(i);
			if (i % 2 == 0 && queryStringParts[i + 1] != "" && typeof queryStringParts[i + 1] != "undefined") {
				queryStringData[queryStringParts[i]] = queryStringParts[i + 1];
			}
		}
		filters.each(function() {
			var filter, filterName;

			filter = $(this);
			filterName = filter.attr("data-filtername");

			if (typeof queryStringData[filterName] != "undefined") {
				setFilter(filter, queryStringData[filterName]);
			} else {
				setFilter(filter);
			}
		});

		// Set filters when changed
		urlParts = location.pathname.split("/");
		if (typeof urlParts[2] != "undefined") {
			category = urlParts[2];
		} else {
			category = null;
		}
		filters.on("click", "a", function(e) {
			var clickedOption, filter, newFilterValue, newFilterValues, newFilterValuesForURL, newPathName;

			clickedOption = $(e.target);

			filter = clickedOption.closest(".classes-filter");
			newFilterValue = clickedOption.attr("data-filtervalue");
			setFilter(filter, newFilterValue);

			// Collate new filter values for inclusion in the URL
			newFilterValuesForURL = {}
			filters.each(function() {
				var filter, filterName, filterValue;

				filter = $(this);
				filterName = filter.attr("data-filtername");
				filterValue = getFilterValue(filter);

				newFilterValuesForURL[filterName] = filterValue;
			});

			// Build new URL and redirect to it
			newLocation = "/classes";
			if (category !== null) {
				newLocation += "/"+category;
			}
			newLocation += "?";
			for (filter_name in newFilterValuesForURL) {
				newLocation += (encodeURIComponent(filter_name)+"="+encodeURIComponent(newFilterValuesForURL[filter_name])+"&");
			}
			newLocation = newLocation.replace(/&$/, "");
			location.replace(newLocation);

			// Stop the form actually submitting
			e.preventDefault();
			return false;
		});
	});

	function getFilterValue(filter) {
		var value;

		value = filter.find(".selected-item").attr("data-filtervalue");
		return value;
	}

	function setFilter(filter, newValue) {
		var item, newLabel;

		if (typeof newValue == "undefined") {
			newValue = filter.attr("data-defaultvalue");
			newLabel = filter.attr("data-defaultlabel");
		} else {
			item = filter.find("a").filter(function() {
				return ($(this).attr("data-filtervalue") == newValue);
			});
			if (item.length == 0) {

				// Set default value
				setFilter(filter);

				return;
			}
			newLabel = item.text();
		}

		if (newValue == filter.attr("data-defaultvalue")) {
			filter.addClass("showing-default");
		} else {
			filter.removeClass("showing-default");
		}

		filter.find(".selected-item").attr("data-filtervalue", newValue).text(newLabel);
	}

})(jQuery);


/*
 * Shopping basket
 */
(function($) {
	$(function() {
		$(".shopping-basket-proceed-to-checkout-form").on("submit", function(e) {
			alert("To do");
			e.preventDefault();
			return false;
		});
	});
})(jQuery);