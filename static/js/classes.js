(function($) {
	$(function() {

		// Set up default options in filters on page load
		var filters = $(".classes-filter");
		filters.each(function() {
			var filter, defaultValue, defaultLabel;

			filter = $(this);

			defaultValue = filter.attr("data-defaultvalue");
			defaultLabel = filter.attr("data-defaultlabel");

			filter.find(".default-option").attr("data-filtervalue", defaultValue).text(defaultLabel);
		});

		// Set filters on page load
		// TODO:WV:20170515:Could do this in page template
		var urlParts = location.pathname.split("/");
		var filternames = ["dates", "ages"];
		var urlPartOffset = 2;
		for (var i in filternames) {
			i = parseInt(i);
			if (typeof urlParts[urlPartOffset + i] != "undefined") {
				setFilter(filternames[i], urlParts[urlPartOffset + i]);
			} else {
				setFilter(filternames[i])
			}
		}

		// Set filters when changed
		filters.on("click", "a", function(e) {
			var clickedOption, filterName, newFilterValue, newFilterValues, newFilterValuesForURL, newPathName;

			clickedOption = $(e.target);

			filterName = clickedOption.closest(".classes-filter").attr("data-filtername");
			if (filterName == "") {
				throw new Error("No filter name supplied");
			}

			newFilterValue = clickedOption.attr("data-filtervalue");

			setFilter(filterName, newFilterValue);

			console.log(filterName, newFilterValue);

			newFilterValuesForURL = [
				getFilterValue("dates"),
				getFilterValue("ages")
			];

			newPathName = "/classes/"+(newFilterValuesForURL.join("/"));
			newPathName = newPathName.replace(/\/+$/, "");

			// Update list
			// TODO:WV:20170515:Use AJAX + history API if possible
			location.pathname = "/classes/"+newFilterValuesForURL.join("/");

			e.preventDefault();
			return false;
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

		if (typeof newValue == "undefined") {
			newValue = filter.attr("data-defaultvalue");
			newLabel = filter.attr("data-defaultlabel");
		} else {
			item = filter.find("a").filter(function() {
				return ($(this).attr("data-filtervalue") == newValue);
			});
			if (item.length == 0) {

				// Set default value
				setFilter(filterName);

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

	function getFilter(filterName) {
		var filter;

		filter = $(".classes-filter").filter(function() {
			return ($(this).attr("data-filtername") == filterName);
		});

		return filter;
	}

})(jQuery);