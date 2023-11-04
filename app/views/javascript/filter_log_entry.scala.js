@() {
/** Autocomplete UI Form. */
$(function() {
    $( "#filter-machine" ).on( "change", function() {
        var searchParams = new URLSearchParams(window.location.search);
        if (searchParams.get("machineId") == this.value) return;
        if (this.value != "") {
            searchParams.set("machineId", this.value);
        } else {
            searchParams.delete("machineId")
        }
        window.location.search = searchParams.toString();
      } );
});
}
