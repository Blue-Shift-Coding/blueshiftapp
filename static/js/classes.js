
/*
 * Filters
 */
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
		// TODO:WV:20170622:Adapt to what filters are actually set in WC, rather than hard-coding dates and ages, or prevent editing of these filters in WC via a Wordpress plugin
		var urlParts = location.pathname.split("/");
		var filternames = ["dates", "ages"];
		var urlPartOffset = 3;
		for (var i in filternames) {
			i = parseInt(i);
			if (typeof urlParts[urlPartOffset + i] != "undefined") {
				setFilter(filternames[i], urlParts[urlPartOffset + i]);
			} else {
				setFilter(filternames[i])
			}
		}
		var category;
		if (typeof urlParts[2] != "undefined") {
			category = urlParts[2];
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

			newFilterValuesForURL = [
				getFilterValue("dates"),
				getFilterValue("ages")
			];

			newPathName = "/classes/"+category+"/"+(newFilterValuesForURL.join("/"));
			newPathName = newPathName.replace(/\/+$/, "");

			// Update list
			location.pathname = newPathName;

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