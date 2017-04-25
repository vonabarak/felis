/**
 * Created by bobr on 2/26/17.
 */

jQuery(document).ready(function($) {
    $(".clickable-row").click(function() {
        window.location = $(this).data("href");
    });
});
