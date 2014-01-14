angular.module('divideBaturDirectives', [])
  .directive('countSummary', function() {
    return {
      'restrict': 'E',
      templateUrl: 'partials/count-summary.html'
    }
  })
  .directive('candidateExcluded', function() {
    return {
      'restrict': 'E',
      templateUrl: 'partials/candidate-excluded.html',
      scope: {
        'round': '=',
        'candidates': '=',
        'parties' : '='
      }
    }
  })
  .directive('candidateElected', function() {
    return {
      'restrict': 'E',
      templateUrl: 'partials/candidate-elected.html',
      scope: {
        'round': '=',
        'candidates': '=',
        'parties' : '='
      }
    }
  })
  .directive('countNotes', function() {
    return {
      'restrict': 'E',
      templateUrl: 'partials/count-notes.html',
      scope: {
        'round': '='
      }
    }
  })
  .directive('stateBadges', function() {
    return {
      'restrict': 'E',
      templateUrl: 'partials/state-badges.html',
      scope: {
        'state': '='
      }
    }
  })
  .directive('candidate', function() {
    return {
      restrict: 'E',
      scope: {
        'id': '=',
        'candidates': '=',
        'parties' : '='
      },
      templateUrl: 'partials/candidate.html'
    };
  });