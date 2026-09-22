(define (problem planning-problem)
(:domain business-context)
(:objects
  certificate
  do
  skip
)
(:init
  (certificate_initial certificate)
  (do_issue do)
)
(:goal (and
  (executed-issue-certificate)
))
)
