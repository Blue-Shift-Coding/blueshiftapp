
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
 * Product options
 */
(function($) {
	$(function() {

		// TODO:WV:20170531:Find a suitable way to behave if there are NO product options (e.g. perhaps dont show the modal at all?)  Or is this not necessary - will there always be options?
		// TODO:WV:20170531:Stop the Javascript error that is triggered if you press escape while the modal is showing (this would be the theme's problem, but good to fix or work-around anyway, perhaps by overriding the escape-button handler)
		$(".classes-results").on("submit", "form.product-options", function(e) {
			var form, productOptionIdsField, productOptionValuesField, ids = [], values = [], purchaseFormTarget, spamInterval;

			$form = $(this);

			// Compile data to submit
			$form.find(".product-option-field").each(function() {
				var field, id, value;

				field = $(this).find("input, select");
				id = field.attr("data-option-id");
				if (id == "") {
					throw new Error("No option ID");
				}
				ids.push(replaceCommas(id));
				value = field.val();
				if (typeof value == "undefined") {
					value = "";
				}
				values.push(replaceCommas(value));
			});

			// Find fields to insert data into
			productOptionIdsField = $form.find("[name=productOptionId]");
			productOptionValuesField = $form.find("[name=productOption]");
			if (productOptionIdsField.length == 0 || productOptionValuesField.length == 0) {
				throw new Error("Missing form field: productOptionId or productOption");
			}

			// Concatenate data into fields
			productOptionIdsField.val(ids.join(","));
			productOptionValuesField.val(values.join(","));

			// Put an order ID in the order-id variable
			// TODO:WV:20170603:Save this on our server first, or immediately after form submission (form could submit to our server, which could forward the user on - it's a GET form)
			$form.find(".order_id input").val(generateHash($form.serialize())+(new Date).getTime());

			// Allow standard form submission (i.e. no 'preventDefault' or 'return false' here)
		});
	});

	// From http://werxltd.com/wp/2010/05/13/javascript-implementation-of-javas-string-hashcode-method/
	function generateHash(string) {
		var hash = 0;
		if (string.length == 0) {
			return hash;
		}
		for (i = 0; i < string.length; i++) {
			char = string.charCodeAt(i);
			hash = ((hash<<5)-hash)+char;
			hash = hash & hash; // Convert to 32bit integer
		}
		return hash;
	}


	/*
	 * This function is for replacing commas with a similar obscure unicode character known as a full-width comma
	 * so that the string can safely be included in a comma-separated list.
	 * Full-width comma: http://www.fileformat.info/info/unicode/char/ff0c/index.htm
	 */
	function replaceCommas(str) {
		return str.replace(",", "，");
	}


	/*
	 * Enable datepickers
	 */
	var weekDaysOnlyOptions = {
		"beforeShowDay": function(date) {
			var dayOfWeek, isWeekDay;

			dayOfWeek = date.getDay();
			isWeekDay = (dayOfWeek > 0 && dayOfWeek < 6);
			return [isWeekDay];
		}
	}
	$(".date-picker").each(function() {
		var options;

		if ($(this).hasClass("weekdays-only")) {
			options = weekDaysOnlyOptions;
		} else {
			options = {}
		}

		$(this).datepicker(options);
	});

})(jQuery);