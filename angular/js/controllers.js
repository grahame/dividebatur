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
    });
}]);

divideBatur.controller('CountRoundDetailCtrl', ['$scope', '$routeParams', '$http', '$timeout', '$location', 'countData',
  function($scope, $routeParams, $http, $timeout, $location, countData) {

    countData.getCount($routeParams.countId, function(data) {
      $scope.round = data.rounds[$routeParams.round - 1];
      $scope.shortname = $routeParams.countId;
      $scope.candidates = data.candidates;
      $scope.parameters = data.parameters;
      $scope.parties = data.parties;
      $scope.first_round = $scope.round.number == 1;
      $scope.last_round = $scope.round.number == data.rounds.length;
      $scope.no_outcomes = ($scope.round.elected.length == 0) && (!$scope.round.excluded) && ($scope.round.note.length == 0);

      var go_round = function(n) {
        $location.path("/count/" + $routeParams.countId + "/round/" + n);        
      }

      $scope.previousRound = function() {
        go_round($scope.round.number - 1);
      }
      $scope.nextRound = function() {
        go_round($scope.round.number + 1);
      }
      $scope.firstRound = function() {
        go_round(1);
      }
      $scope.lastRound = function() {
        go_round(data.rounds.length);
      }
      $scope.overview = function() {
        $location.path("/count/" + $routeParams.countId);
      }
  });
}]);
