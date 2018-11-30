@import PersonController.FormID.machineId

@(userId: Int) {
/** Autocomplete UI Form. */
$(function() {

    $(".autocomplete-machine").autocomplete({
        source: "@JavaScript(routes.MachineController.findQualificableMachine(userId, None).url)",
        minLength: 1,
        select: function( event, ui ) {
            event.preventDefault();
            this.value = ui.item.label;
            $("#@machineId").val(ui.item.value);
        },
        focus: function( event, ui ) {
            event.preventDefault();
            this.value = ui.item.label;
            $("#@machineId").val(ui.item.value);
        }
    });

});
}
