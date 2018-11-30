@import TokenController.FormKey.findPersonId

@() {
/** Autocomplete UI Form. */
$(function() {

    $(".autocomplete-person").autocomplete({
        source: "@JavaScript(routes.PersonController.findPerson(None).url)",
        minLength: 1,
        select: function( event, ui ) {
            event.preventDefault();
            this.value = ui.item.label;
            $("#@findPersonId").val(ui.item.value);
        },
        focus: function( event, ui ) {
            event.preventDefault();
            this.value = ui.item.label;
            $("#@findPersonId").val(ui.item.value);
        }
    });

});
}
