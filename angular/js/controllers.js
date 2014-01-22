var divideBatur = angular.module('divideBaturControllers', []);

divideBatur.controller('CountCtrl', ['$scope', '$http',
  function ($scope, $http) {
    $http.get('data/count.json').success(function(data) {
      $scope.counts = data['counts'];
      $scope.count = $scope.counts[0];
      $scope.state = data['state'];
      $scope.house = data['house'];
  });
}]);

divideBatur.controller('CountDetailCtrl', ['$scope', '$routeParams', '$http', '$timeout', 'countData',
  function($scope, $routeParams, $http, $timeout, countData) {

    countData.getCount($routeParams.countId, function(data) {
      $scope.summary = data.summary;
      $scope.shortname = $routeParams.countId;
      $scope.candidates = data.candidates;
      $scope.rounds = data.rounds.length;
      $scope.parameters = data.parameters;
      $scope.parties = data.parties;
      $scope.data_link = countData.dataPath($scope.shortname);
    });
}]);

divideBatur.controller('CountRoundDetailCtrl', ['$scope', '$routeParams', '$document', '$http', '$timeout', '$location', 'countData',
  function($scope, $routeParams, $document, $http, $timeout, $location, countData) {

    countData.getCount($routeParams.countId, function(data) {
      $scope.round = data.rounds[$routeParams.round - 1];
      $scope.shortname = $routeParams.countId;
      $scope.candidates = data.candidates;
      $scope.parameters = data.parameters;
      $scope.parties = data.parties;
      $scope.rounds = data.rounds.length;
      $scope.first_round = $scope.round.number == 1;
      $scope.last_round = $scope.round.number == data.rounds.length;
      $scope.no_outcomes = ($scope.round.elected.length == 0) && (!$scope.round.excluded) && ($scope.round.note.length == 0);

      // this seems wrong, come back to it...
      // $document.bind('keypress', function(event) {
      //   console.log(event.charCode);
      //   if (event.charCode == 106) { // j
      //     $scope.nextRound();
      //     $scope.$apply();
      //   } else if (event.charCode == 107) {
      //     $scope.previousRound();
      //     $scope.$apply();
      //   }
      // });

  });
}]);
