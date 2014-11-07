from __future__ import division
from scrapy.contrib.statsmailer import StatsMailer
# import datetime

#
# Override extensions StatsMailer that sends email
# by catching spider closed signal, so that only certain
# stats are emailed and only upon error.
# Need to add this in EXTENSIONS under settings.py
#


class ErrorStatsMailer(StatsMailer):

    def spider_closed(self, spider):
        spider_stats = self.stats.get_stats(spider)

        # Reasons to send email.

        # Items scraped too low
        ignoreTooFewSpiders = ['BGbet', ]
        too_few_items = False
        items_scraped = self.stats.get_value('item_scraped_count')
        if items_scraped < 40 and spider.name not in ignoreTooFewSpiders:
            too_few_items = True

        # Ratio of requests to responses bad
        bad_resp_req_ratio = False
        resp_count = self.stats.get_value('downloader/response_status_count/200')
        req_count = self.stats.get_value('downloader/request_count')
        if resp_count and req_count:
            if (resp_count/req_count) < 0.35:
                bad_resp_req_ratio = True
        else:
            # If resp or req count missing set bad resp
            bad_resp_req_ratio = True

        # Finished for some reason other than 'finished'
        bad_finish = False
        reason = self.stats.get_value('finish_reason')
        if reason != 'finished':
            bad_finish = True

        # Errors
        ignoreErrorSpiders = []   # ['Interwetten', ]  # Books to not email on err
        any_errors = False
        # if ('log_count/ERROR' in self.stats.get_stats(spider).keys() and
        #    spider.name not in ignoreErrorSpiders):
        # Use spider exceptions as this works also when multiple spiders called
        # from same script(also only gives uncaught excepotions not errs we
        # know)
        if ('spider_exceptions' in self.stats.get_stats(spider).keys() and
           spider.name not in ignoreErrorSpiders):
            print '[DEBUG] Spider name is: %s' % spider.name
            any_errors = True

        if (bad_finish or bad_resp_req_ratio or too_few_items or any_errors):
            # Send email if error.

            # Get duration
            start = self.stats.get_value('start_time')
            finish = self.stats.get_value('finish_time')
            tdelta = finish - start
            mins = (tdelta.total_seconds()/60)

            # Get error count
            # num_error = self.stats.get_value('spider_exceptions', 0)

            # Build subject
            subject = ('[%s] errors for %s spider. Scrape took %.2f mins'
                       % (reason, spider.name, mins))

            # Build body
            body = "Vital stats\n\n"
            body += "Scaped item count: %s\n" % items_scraped
            if resp_count and req_count:
                body += "Response/Request ratio: %s\n" % (resp_count/req_count)
            else:
                body += "Either resp count or req_count was None"
            body += "\n\n"

            body += "Global stats\n\n"
            body += "\n".join("%-50s : %s" % i for i
                              in self.stats.get_stats().items())

            body += "\n\n%s stats\n\n" % spider.name
            body += "\n".join("%-50s : %s" % i for i in spider_stats.items())

            # Send mail
            return self.mail.send(self.recipients, subject, body)
        else:
            pass
