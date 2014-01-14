var divideBatur = angular.module('divideBaturControllers', []);
 
divideBatur.controller('CountListCtrl', ['$scope', '$http',
    function ($scope, $http) {
        $http.get('data/count.json').success(function(data) {
            $scope.counts = data;
            $scope.count = $scope.counts[0];
        });
    }]);

divideBatur.controller('CountDetailCtrl', ['$scope', '$routeParams', '$http',
  function($scope, $routeParams, $http) {
    $http.get('data/' + $routeParams.countId + '.json').success(function(data) {
      $scope.summary = data.summary;
      $scope.candidates = data.candidates;
      $scope.first_round = data.rounds[0];
      $scope.later_rounds = data.rounds.slice(1, data.rounds.length);
      $scope.rounds = data.rounds.length;
      $scope.parameters = data.parameters;
      $scope.parties = data.parties;
    });
  }]);
