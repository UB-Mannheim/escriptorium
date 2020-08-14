function exitonboarding() {
  $.ajax({type: 'PUT', url:'/api/users/onboarding/',
          contentType: "application/json; charset=utf-8",
          data:JSON.stringify({
            onboarding : "False",
            })

      }).done($.proxy(function(data){
            }, this)).fail(function(data) {
                alert(data);
            });

}
