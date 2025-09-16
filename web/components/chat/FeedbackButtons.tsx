'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  Star,
  Send,
} from 'lucide-react';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { cn } from '@/lib/utils';

interface FeedbackButtonsProps {
  traceId: string;
  sessionId: string;
  onFeedback: (feedback: any) => void;
}

export function FeedbackButtons({
  traceId,
  sessionId,
  onFeedback,
}: FeedbackButtonsProps) {
  const [thumbsUp, setThumbsUp] = useState<boolean | null>(null);
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const [showComment, setShowComment] = useState(false);

  const handleThumbsFeedback = (isPositive: boolean) => {
    const newValue = thumbsUp === isPositive ? null : isPositive;
    setThumbsUp(newValue);
    
    if (newValue !== null) {
      onFeedback({
        traceId,
        sessionId,
        thumbsUp: newValue,
      });
    }
  };

  const handleRating = (value: number) => {
    const newRating = rating === value ? null : value;
    setRating(newRating);
    
    if (newRating !== null) {
      onFeedback({
        traceId,
        sessionId,
        rating: newRating,
      });
    }
  };

  const handleCommentSubmit = () => {
    if (comment.trim()) {
      onFeedback({
        traceId,
        sessionId,
        comment: comment.trim(),
        rating,
        thumbsUp,
      });
      setComment('');
      setShowComment(false);
    }
  };

  return (
    <div className="flex items-center gap-2 mt-2">
      {/* Thumbs up/down */}
      <div className="flex gap-1">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => handleThumbsFeedback(true)}
          className={cn(
            'h-8 w-8 p-0',
            thumbsUp === true && 'text-green-600 bg-green-100 hover:bg-green-200'
          )}
        >
          <ThumbsUp className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => handleThumbsFeedback(false)}
          className={cn(
            'h-8 w-8 p-0',
            thumbsUp === false && 'text-red-600 bg-red-100 hover:bg-red-200'
          )}
        >
          <ThumbsDown className="h-4 w-4" />
        </Button>
      </div>

      {/* Star rating */}
      <div className="flex gap-1 border-l pl-2">
        {[1, 2, 3, 4, 5].map((value) => (
          <Button
            key={value}
            variant="ghost"
            size="sm"
            onClick={() => handleRating(value)}
            className="h-8 w-8 p-0"
          >
            <Star
              className={cn(
                'h-4 w-4',
                rating && value <= rating
                  ? 'fill-yellow-500 text-yellow-500'
                  : 'text-muted-foreground'
              )}
            />
          </Button>
        ))}
      </div>

      {/* Comment button */}
      <Popover open={showComment} onOpenChange={setShowComment}>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-1"
          >
            <MessageSquare className="h-4 w-4" />
            <span className="text-xs">Comment</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-80">
          <div className="space-y-2">
            <h4 className="font-medium text-sm">Add a comment</h4>
            <Textarea
              placeholder="Share your feedback..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="min-h-[80px]"
            />
            <Button
              onClick={handleCommentSubmit}
              disabled={!comment.trim()}
              size="sm"
              className="w-full"
            >
              <Send className="h-4 w-4 mr-1" />
              Send Feedback
            </Button>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}