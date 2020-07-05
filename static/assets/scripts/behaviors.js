
jQuery(document).ready(function () {
    jQuery("#heat")

        .click(function () {
            jQuery("input[name='tunit']").val(tempunit);
            jQuery("form[name='tt']").submit();
        });
    var temp = parseFloat(cputemp);
    if (isNaN(temp)) {
        jQuery("#heat").html("n/a");
    } else {
        jQuery("#heat").html((tempunit == "F" ? Math.round(10 * (9 / 5 * cputemp + 32)) / 10 : cputemp) + "&deg;" + tempunit);
    }


});
