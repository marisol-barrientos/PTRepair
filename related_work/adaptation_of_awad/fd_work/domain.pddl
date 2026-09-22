(define (domain business-context)
(:requirements :strips)
(:predicates
  (executed-receive-application)
  (executed-issue-certificate)
  (certificate_initial ?obj)
  (certificate_valid ?obj)
  (do_issue ?obj)
  (skip_issue ?obj)
)
; ACTIONS
(:action execute_receive_application1
  :parameters(?certificate )
  :precondition (and (certificate_initial ?certificate) )
  :effect (and (executed-receive-application) (certificate_initial ?certificate) )
)
(:action execute_issue_certificate1
  :parameters(?certificate ?do )
  :precondition (and (certificate_initial ?certificate) (do_issue ?do) )
  :effect (and (executed-issue-certificate) (certificate_valid ?certificate) (not (certificate_initial ?certificate)) )
)
)
