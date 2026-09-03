'use strict';
const EventEmitter = require('events');

class Queue extends EventEmitter {
  constructor(options) {
    super();
    options = options || {};
    this.concurrency = options.concurrency || Infinity;
    this.timeout = options.timeout || 0;
    this.autostart = !!options.autostart;
    this.results = options.results || null;
    this.pending = 0;
    this.jobs = [];
    this.running = false;
  }

  push(...jobs) {
    this.jobs.push(...jobs);
    if (this.autostart) this.start();
    return this.jobs.length;
  }

  unshift(...jobs) {
    this.jobs.unshift(...jobs);
    if (this.autostart) this.start();
    return this.jobs.length;
  }

  start(callback) {
    if (callback) this.once('end', (err) => callback(err));
    if (this.running) return this;
    this.running = true;
    this._runNext();
    return this;
  }

  stop() {
    this.running = false;
    return this;
  }

  end(err) {
    this.running = false;
    this.jobs.length = 0;
    this.pending = 0;
    this.emit('end', err);
  }

  _runNext() {
    if (!this.running) return;
    if (this.jobs.length === 0 && this.pending === 0) {
      this.end();
      return;
    }
    while (this.running && this.pending < this.concurrency && this.jobs.length > 0) {
      const job = this.jobs.shift();
      this.pending += 1;
      let settled = false;
      const done = (err, result) => {
        if (settled) return;
        settled = true;
        this.pending -= 1;
        if (err) {
          this.emit('error', err, job);
          this.end(err);
          return;
        }
        if (this.results) this.results.push(result);
        this.emit('success', result, job);
        this._runNext();
      };
      try {
        if (job.length > 0) {
          job(done);
        } else {
          const ret = job();
          if (ret && typeof ret.then === 'function') {
            ret.then((r) => done(null, r), (e) => done(e));
          } else {
            done(null, ret);
          }
        }
      } catch (e) {
        done(e);
      }
    }
  }
}

module.exports = function queue(options) {
  return new Queue(options);
};
module.exports.Queue = Queue;
